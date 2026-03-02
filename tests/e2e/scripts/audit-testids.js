#!/usr/bin/env node
/**
 * audit-testids.js
 *
 * Scans Vue SFC <template> blocks for interactive elements (buttons, inputs,
 * selects, links, @click handlers) that are missing a data-testid attribute.
 *
 * Usage:
 *   node tests/e2e/scripts/audit-testids.js [--dir=frontend/src] [--json] [--fail-below=80]
 *
 * Options:
 *   --dir=PATH        Vue source directory to scan (default: frontend/src)
 *   --json            Output results as JSON (for CI parsing)
 *   --fail-below=N    Exit code 1 if overall coverage < N% (default: 70)
 *
 * Exit codes:
 *   0 — Coverage meets threshold
 *   1 — Coverage below threshold or parse errors
 */

import { readFileSync, readdirSync, statSync } from 'fs';
import { join, relative } from 'path';
import { fileURLToPath } from 'url';
import { dirname } from 'path';

const __dirname = dirname(fileURLToPath(import.meta.url));
const ROOT = join(__dirname, '..', '..', '..');

// --- CLI argument parsing ---
const args = process.argv.slice(2);
const getArg = (prefix) => {
  const arg = args.find(a => a.startsWith(prefix));
  return arg ? arg.slice(prefix.length) : null;
};
const jsonOutput = args.includes('--json');
const sourceDir = join(ROOT, getArg('--dir=') || 'frontend/src');
const failBelow = parseInt(getArg('--fail-below=') || '70', 10);

// --- Severity levels ---
// HIGH: interactive elements that always need data-testid
// MEDIUM: clickable or navigation elements
// LOW: display-only elements that help debugging
const HIGH_PATTERNS = [
  /<button(?![^>]*data-testid)[^>]*>/g,
  /<input(?![^>]*data-testid)[^>]*>/g,
  /<select(?![^>]*data-testid)[^>]*>/g,
  /<textarea(?![^>]*data-testid)[^>]*>/g,
];

const MEDIUM_PATTERNS = [
  /<a(?:\s+[^>]*)?\s+(?:href|@click)(?![^>]*data-testid)[^>]*>/g,
  /<(?:div|span|li|td)(?![^>]*data-testid)[^>]*@click[^>]*>/g,
];

const LOW_PATTERNS = [
  /<(?:div|section|article|main|aside)(?![^>]*data-testid)[^>]*class=[^>]*>/g,
];

// Counts elements WITH data-testid for the same element types
const COVERED_PATTERNS = [
  /<(?:button|input|select|textarea|a)(?=[^>]*data-testid)[^>]*>/g,
  /<(?:div|span|li|td)(?=[^>]*data-testid)[^>]*@click[^>]*>/g,
];

// --- File discovery ---
function walkVueFiles(dir, files = []) {
  try {
    const entries = readdirSync(dir);
    for (const entry of entries) {
      const fullPath = join(dir, entry);
      const stat = statSync(fullPath);
      if (stat.isDirectory()) {
        // Skip node_modules and dist
        if (entry === 'node_modules' || entry === 'dist' || entry === '.git') continue;
        walkVueFiles(fullPath, files);
      } else if (entry.endsWith('.vue')) {
        files.push(fullPath);
      }
    }
  } catch {
    // Skip unreadable directories
  }
  return files;
}

// --- Template extraction ---
function extractTemplate(source) {
  const start = source.indexOf('<template');
  if (start === -1) return '';
  const end = source.lastIndexOf('</template>');
  if (end === -1) return source.slice(start);
  return source.slice(start, end + '</template>'.length);
}

// --- Count regex matches ---
function countMatches(text, pattern) {
  const re = new RegExp(pattern.source, pattern.flags);
  let count = 0;
  while (re.exec(text) !== null) count++;
  return count;
}

// --- Audit a single file ---
function auditFile(filePath) {
  const source = readFileSync(filePath, 'utf8');
  const template = extractTemplate(source);
  if (!template) return null;

  const missing = { high: [], medium: [], low: [] };
  let highCount = 0, mediumCount = 0, lowCount = 0;
  let coveredCount = 0, totalInteractive = 0;

  for (const pattern of HIGH_PATTERNS) {
    const matches = template.match(new RegExp(pattern.source, pattern.flags)) || [];
    highCount += matches.length;
  }
  for (const pattern of MEDIUM_PATTERNS) {
    const matches = template.match(new RegExp(pattern.source, pattern.flags)) || [];
    mediumCount += matches.length;
  }
  for (const pattern of LOW_PATTERNS) {
    const matches = template.match(new RegExp(pattern.source, pattern.flags)) || [];
    lowCount += matches.length;
  }
  for (const pattern of COVERED_PATTERNS) {
    const matches = template.match(new RegExp(pattern.source, pattern.flags)) || [];
    coveredCount += matches.length;
  }

  totalInteractive = highCount + mediumCount + coveredCount;
  const coverage = totalInteractive === 0 ? 100 :
    Math.round((coveredCount / totalInteractive) * 100);

  if (highCount > 0) missing.high.push(`${highCount} interactive element(s) without data-testid`);
  if (mediumCount > 0) missing.medium.push(`${mediumCount} clickable element(s) without data-testid`);
  if (lowCount > 0) missing.low.push(`${lowCount} display element(s) missing data-testid`);

  return {
    file: relative(ROOT, filePath),
    coverage,
    missing: {
      high: highCount,
      medium: mediumCount,
      low: lowCount,
    },
    covered: coveredCount,
    total: totalInteractive,
  };
}

// --- Main ---
function main() {
  const vueFiles = walkVueFiles(sourceDir);

  if (vueFiles.length === 0) {
    console.error(`No .vue files found in: ${sourceDir}`);
    process.exit(1);
  }

  const results = vueFiles
    .map(auditFile)
    .filter(Boolean)
    .filter(r => r.total > 0); // Only report files with interactive elements

  // Sort by severity (most missing HIGH first, then MEDIUM, then by coverage ascending)
  results.sort((a, b) => {
    if (b.missing.high !== a.missing.high) return b.missing.high - a.missing.high;
    if (b.missing.medium !== a.missing.medium) return b.missing.medium - a.missing.medium;
    return a.coverage - b.coverage;
  });

  const totalCovered = results.reduce((sum, r) => sum + r.covered, 0);
  const totalInteractive = results.reduce((sum, r) => sum + r.total, 0);
  const overallCoverage = totalInteractive === 0 ? 100 :
    Math.round((totalCovered / totalInteractive) * 100);

  const highIssues = results.filter(r => r.missing.high > 0);
  const mediumIssues = results.filter(r => r.missing.medium > 0 && r.missing.high === 0);
  const cleanFiles = results.filter(r => r.missing.high === 0 && r.missing.medium === 0);

  if (jsonOutput) {
    console.log(JSON.stringify({
      summary: {
        overallCoverage,
        totalFiles: results.length,
        totalInteractive,
        totalCovered,
        highIssueFiles: highIssues.length,
        mediumIssueFiles: mediumIssues.length,
        cleanFiles: cleanFiles.length,
        meetsThreshold: overallCoverage >= failBelow,
      },
      highPriority: highIssues,
      mediumPriority: mediumIssues,
    }, null, 2));
  } else {
    // Human-readable output
    console.log('\n' + '='.repeat(60));
    console.log('  data-testid Coverage Audit');
    console.log('='.repeat(60));
    console.log(`\n  Overall Coverage: ${overallCoverage}% (threshold: ${failBelow}%)`);
    console.log(`  Files scanned:    ${results.length}`);
    console.log(`  Interactive elems: ${totalInteractive} total, ${totalCovered} covered`);
    console.log(`  Threshold:        ${overallCoverage >= failBelow ? '✅ PASS' : '❌ FAIL'}`);

    if (highIssues.length > 0) {
      console.log('\n' + '─'.repeat(60));
      console.log('  🔴 HIGH — Buttons/Inputs/Selects missing data-testid');
      console.log('─'.repeat(60));
      for (const r of highIssues.slice(0, 20)) {
        console.log(`  [${r.coverage}%] ${r.file}`);
        console.log(`         ${r.missing.high} interactive element(s) missing data-testid`);
      }
      if (highIssues.length > 20) {
        console.log(`  ... and ${highIssues.length - 20} more`);
      }
    }

    if (mediumIssues.length > 0) {
      console.log('\n' + '─'.repeat(60));
      console.log('  🟡 MEDIUM — Clickable divs/links missing data-testid');
      console.log('─'.repeat(60));
      for (const r of mediumIssues.slice(0, 10)) {
        console.log(`  [${r.coverage}%] ${r.file}`);
        console.log(`         ${r.missing.medium} clickable element(s) missing data-testid`);
      }
      if (mediumIssues.length > 10) {
        console.log(`  ... and ${mediumIssues.length - 10} more`);
      }
    }

    if (cleanFiles.length > 0) {
      console.log(`\n  ✅ ${cleanFiles.length} file(s) fully covered (no HIGH/MEDIUM issues)`);
    }

    console.log('\n' + '='.repeat(60));
    if (overallCoverage < failBelow) {
      console.log(`  ❌ FAILED: Coverage ${overallCoverage}% < threshold ${failBelow}%`);
      console.log(`  Fix HIGH priority items first (buttons, inputs, selects).`);
    } else {
      console.log(`  ✅ PASSED: Coverage ${overallCoverage}% >= threshold ${failBelow}%`);
    }
    console.log('='.repeat(60) + '\n');
  }

  process.exit(overallCoverage >= failBelow ? 0 : 1);
}

main();
