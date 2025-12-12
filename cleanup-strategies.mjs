import fs from 'fs';

const token = fs.readFileSync('tests/config/.auth-token', 'utf8').trim();

async function deleteStrategies() {
  try {
    const response = await fetch('http://localhost:8000/api/v1/autopilot/strategies?limit=100', {
      headers: { Authorization: 'Bearer ' + token }
    });
    const data = await response.json();
    console.log('Found', data.data?.length || 0, 'strategies');

    if (!data.data) return;

    for (const strategy of data.data) {
      console.log('Deleting:', strategy.id, strategy.name);
      await fetch('http://localhost:8000/api/v1/autopilot/strategies/' + strategy.id, {
        method: 'DELETE',
        headers: { Authorization: 'Bearer ' + token }
      });
    }
    console.log('Done deleting');
  } catch(e) {
    console.error('Error:', e.message);
  }
}

deleteStrategies();
