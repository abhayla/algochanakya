Feature: Strategy Library
  As an options trader
  I want to browse pre-built option strategies
  So that I can quickly deploy proven trading setups

  Background:
    Given I am logged in as a verified user
    And I am on the Strategy Library page

  # ============ BROWSE STRATEGIES ============

  @happy @smoke
  Scenario: View all strategy categories
    Then I should see the following category filters:
      | Category | Display |
      | bullish  | Bullish |
      | bearish  | Bearish |
      | neutral  | Neutral |
      | volatile | Volatile |
      | income   | Income |
      | advanced | Advanced |
    And I should see at least 20 strategy cards

  @happy
  Scenario: Filter strategies by category
    When I click on the "neutral" category filter
    Then I should only see strategies with category "neutral"
    And I should see "Iron Condor" in the results
    And I should see "Short Strangle" in the results
    And I should NOT see "Bull Call Spread" in the results

  @happy
  Scenario: Search for a strategy
    When I type "iron" in the search box
    Then I should see "Iron Condor" in the results
    And I should see "Iron Butterfly" in the results
    And I should NOT see "Bull Put Spread" in the results

  @edge
  Scenario: Search with no results
    When I type "xyz123nonexistent" in the search box
    Then I should see "No strategies found" message
    And I should see a "Clear search" button

  # ============ STRATEGY WIZARD ============

  @happy @critical
  Scenario: Complete strategy wizard for bullish outlook
    When I click the "Strategy Wizard" button
    Then I should see the wizard modal

    When I select "Bullish" for market outlook
    And I click "Next"
    Then I should be on step 2

    When I select "High IV" for expected volatility
    And I click "Next"
    Then I should be on step 3

    When I select "Low" for risk appetite
    And I click "Get Recommendations"
    Then I should see at least 3 strategy recommendations
    And "Bull Put Spread" should be in the top 3 recommendations
    And each recommendation should show:
      | Field            |
      | Match Percentage |
      | Reasons          |
      | Win Probability  |

  @happy
  Scenario Outline: Wizard recommends appropriate strategies
    When I complete the wizard with:
      | Outlook   | Volatility   | Risk   |
      | <outlook> | <volatility> | <risk> |
    Then "<expected_strategy>" should be in the recommendations

    Examples:
      | outlook  | volatility | risk   | expected_strategy    |
      | bullish  | high_iv    | low    | Bull Put Spread      |
      | bearish  | high_iv    | low    | Bear Call Spread     |
      | neutral  | high_iv    | medium | Iron Condor          |
      | volatile | low_iv     | medium | Long Straddle        |

  @edge
  Scenario: Wizard back navigation
    Given I am on step 3 of the wizard
    When I click "Back"
    Then I should be on step 2
    And my previous selection should be preserved

    When I click "Back" again
    Then I should be on step 1
    And my previous selection should be preserved

  # ============ STRATEGY DETAILS ============

  @happy
  Scenario: View strategy details
    When I click "View Details" on "Iron Condor"
    Then I should see the strategy details modal
    And I should see the following sections:
      | Section           |
      | Description       |
      | When to Use       |
      | Pros              |
      | Cons              |
      | Common Mistakes   |
      | Exit Rules        |
    And I should see these metrics:
      | Metric          | Value    |
      | Max Profit      | Limited  |
      | Max Loss        | Limited  |
      | Risk Level      | Medium   |
    And I should see Greeks badges: "Theta+" and "Delta Neutral"

  @happy
  Scenario: Close strategy details modal
    Given the strategy details modal is open
    When I click the close button
    Then the modal should close
    And I should see the strategy library page

  # ============ DEPLOY STRATEGY ============

  @happy @critical
  Scenario: Deploy Iron Condor strategy
    When I click "Deploy" on "Iron Condor"
    Then I should see the deploy modal
    And underlying should default to "NIFTY"

    When I select an expiry
    And I set lots to "1"
    Then I should see 4 legs preview

    When I click "Create Strategy"
    Then I should see success message
    And "View Strategy" button should be visible

  @happy
  Scenario: Change underlying in deploy modal
    Given the deploy modal is open for "Iron Condor"
    When I change underlying to "BANKNIFTY"
    Then the lot size display should change to 15

  @edge
  Scenario: Deploy with multiple lots
    Given the deploy modal is open for "Bull Call Spread"
    When I set lots to "3"
    Then lot size display should show multiplied quantity

  # ============ STRATEGY COMPARISON ============

  @happy
  Scenario: Compare two strategies
    When I click the compare icon on "Iron Condor"
    And I click the compare icon on "Iron Butterfly"
    Then the comparison bar should appear
    And it should show "2 strategies selected"

    When I click "Compare"
    Then I should see the comparison modal
    And I should see side-by-side metrics

  @edge
  Scenario: Cannot compare more than 4 strategies
    Given I have 4 strategies selected for comparison
    When I try to add a 5th strategy
    Then I should see an error message about maximum limit

  @edge
  Scenario: Clear comparison selection
    Given I have 3 strategies selected for comparison
    When I click "Clear" on the comparison bar
    Then the comparison bar should disappear
    And no strategies should be selected
