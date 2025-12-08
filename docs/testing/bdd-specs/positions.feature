Feature: Positions Management
  As an options trader
  I want to view and manage my open F&O positions
  So that I can monitor P&L and exit trades

  Background:
    Given I am logged in
    And I have open F&O positions
    And I am on the Positions page

  # ============ VIEW POSITIONS ============

  @happy @smoke
  Scenario: View day positions
    Given the "Day" tab is selected
    Then I should see my intraday positions
    And each position should show:
      | Field           |
      | Instrument      |
      | Product         |
      | Quantity        |
      | Average Price   |
      | LTP             |
      | Day Change      |
      | P&L             |
      | Change %        |
    And total P&L should be displayed in the header

  @happy
  Scenario: View net positions
    When I click the "Net" tab
    Then I should see my net (carried forward) positions
    And the P&L should reflect overall position P&L

  @happy
  Scenario: Positions auto-refresh
    Given auto-refresh is enabled
    When 5 seconds pass
    Then positions should be refreshed
    And LTP and P&L should be updated

  @edge
  Scenario: No open positions
    Given I have no open positions
    Then I should see "No Open Positions" message
    And I should see a link to "Go to Option Chain"

  # ============ EXIT POSITIONS ============

  @happy @critical
  Scenario: Exit position at market price
    When I click "Exit" on a NIFTY 26000 CE position
    Then I should see the exit modal
    And "MARKET" should be selected by default

    When I click "Exit Position"
    Then an opposite order should be placed
    And I should see "Order placed successfully"
    And the position should be removed from the list

  @happy
  Scenario: Exit position at limit price
    Given the exit modal is open
    When I select "LIMIT" order type
    And I enter price "125.50"
    And I click "Exit Position"
    Then a limit order should be placed at 125.50

  @happy @critical
  Scenario: Exit all positions
    When I click "Exit All" button
    Then I should see a confirmation dialog
    And the dialog should warn about exiting all positions

    When I click "Yes, Exit All"
    Then all positions should have exit orders placed
    And I should see the number of orders placed

  @edge
  Scenario: Cancel exit modal
    Given the exit modal is open
    When I click "Cancel" or the X button
    Then the modal should close
    And no order should be placed

  # ============ ADD TO POSITION ============

  @happy
  Scenario: Add to existing long position
    Given I have a long position in NIFTY 26000 CE
    When I click "Add" on that position
    Then I should see the add modal
    And "BUY" should be selected

    When I enter quantity "75"
    And I enter price "130"
    And I click "Add to Position"
    Then a buy order should be placed
    And I should see "Order placed successfully"

  @happy
  Scenario: Add to existing short position
    Given I have a short position in NIFTY 26000 PE
    When I click "Add" on that position
    And I select "SELL"
    And I enter quantity "75"
    And I enter price "45"
    And I click "Add to Position"
    Then a sell order should be placed

  # ============ P&L DISPLAY ============

  @happy
  Scenario: Profit position styling
    Given I have a profitable position
    Then the P&L column should be green
    And the row should have a green tint

  @happy
  Scenario: Loss position styling
    Given I have a losing position
    Then the P&L column should be red
    And the row should have a red tint

  @happy
  Scenario: Total P&L calculation
    Given I have multiple positions
    Then total P&L should be the sum of all position P&Ls
    And total P&L box should be green if positive
    And total P&L box should be red if negative

  # ============ SUMMARY SECTION ============

  @happy
  Scenario: View positions summary
    Then I should see the summary section with:
      | Metric            |
      | Total Positions   |
      | Total Quantity    |
      | Realized P&L      |
      | Unrealized P&L    |
      | Total Margin      |

  @happy
  Scenario: Summary updates on position changes
    When a position is exited
    Then the summary should be updated
    And realized P&L should include the closed position's P&L
