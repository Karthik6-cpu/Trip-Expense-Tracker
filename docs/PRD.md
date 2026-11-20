# Trip Expense Tracker

A web page where one trip organizer records shared expenses and, at the end of the trip, sees what each friend owes them.

## Problem Statement

On a trip with friends, one person pays the bills and later has to remember who took part in each one. Some bills include the whole group. Others include only a few people. Working out each friend's share by hand is slow, and a missed name or a wrong split causes arguments at the end of the trip.

The organizer needs one place to list friends, record each bill, and see a clear amount owed by each friend.

## Target Users

- **Trip organizer.** The only person who opens the page. They add friends, enter every expense, review spending by person, and run settle at the end of the trip.
- **Trip friends.** People on the trip whose shares are calculated. They do not open the page. The organizer uses the settle result to tell each friend what they owe.

## User Stories

1. As a trip organizer, I want to add friends by name, without accounts, so that I can track the trip by myself.
2. As a trip organizer, I want to record an expense with a date, a description, and an amount so that each bill is clear later.
3. As a trip organizer, I want to choose which friends shared an expense so that people who were not part of it are left out.
4. As a trip organizer, I want my own share included on every expense so that friends owe only their portion.
5. As a trip organizer, I want each expense split equally so that I do not calculate shares by hand.
6. As a trip organizer, I want to see expenses for one friend so that I can check that person's charges.
7. As a trip organizer, I want a settle action at the end of the trip so that I can see what each friend owes me.
8. As a trip organizer, I want to clear the current trip and start over so that I can run one trip at a time.
9. As a trip organizer, I want to edit or remove a friend or an expense so that a mistake can be fixed before settle.
10. As a trip organizer, I want to enter a custom share for a friend so that an unequal bill can be recorded when an equal split is unfair.

## Features

### Must Have

- **One organizer, no accounts.** The page opens ready to use. There is no sign-in, no password, and no second user. Supports stories 1 and 7.
- **Add friends.** The organizer adds each friend with a name. Supports story 1.
- **Record an expense.** Each expense stores a date, a short description, and an amount in one currency for the whole trip. Supports story 2.
- **Choose who shared it.** For each expense, the organizer selects one or more friends. Friends who are not selected do not share that expense. Supports story 3.
- **Organizer is always included.** Every expense is shared by the organizer plus the selected friends. The organizer's share is their own cost. It is never shown as money they owe. Supports story 4.
- **Equal split.** The amount is divided into equal shares across the organizer and the selected friends. Each selected friend owes the organizer one share. If the amount does not divide evenly, every friend still owes the same share, and any leftover smallest unit stays in the organizer's own share. The shares add up to the expense amount. Supports story 5.
- **Expenses by person.** A view lists each friend, the expenses they were selected on, their share of each of those expenses, and their total. Supports story 6.
- **Settle.** One action shows each friend and the total they owe the organizer, which is the sum of their shares. It also shows the trip total and the organizer's own shares, which are not debts. Supports story 7.
- **One trip, then start over.** The page holds a single trip. Start over removes all friends and expenses so a new trip can be entered. Supports story 8.

Worked example the settle result must match:

| Expense | Amount | Friends selected | People sharing | Each share | Friend owes |
| --- | ---: | --- | ---: | ---: | --- |
| Dinner | 120 | Asha, Ben | 3 (organizer + 2) | 40 | Asha 40, Ben 40 |
| Snacks | 50 | Cara | 2 (organizer + 1) | 25 | Cara 25 |
| Taxi | 90 | Asha, Ben, Cara | 4 (organizer + 3) | 22.50 | Asha 22.50, Ben 22.50, Cara 22.50 |

Settle: Asha owes 62.50, Ben owes 62.50, Cara owes 47.50. The organizer's own shares are 87.50 and are not a debt. Trip total is 260.

### Should Have

- **Edit and remove.** The organizer can change or remove a friend's name, and can change or remove an expense, before settle. Removing a friend updates any expense that included them, and the shares are recalculated. Supports story 9.

### Nice to Have

- **Custom shares.** For one expense, the organizer can type each selected friend's amount instead of using an equal split. The organizer's own share is what remains. Supports story 10.

## Success Metrics

1. In one sitting, with no second person using the page, the organizer adds 3 friends, enters 3 expenses that use different subsets of those friends, and opens settle.
2. For the worked example above, settle shows Asha 62.50, Ben 62.50, and Cara 47.50, and the expenses-by-person view shows the same totals.
3. After start over, the friends list and the expense list are empty, and a new expense can be added.

## Constraints and Assumptions

- This is a short workshop project that one student builds and demos alone.
- The product is a web page opened in a browser.
- The organizer paid every expense.
- The organizer's share is part of every expense, even when their name is not in the friend list.
- Friends never open the page.
- The page keeps one trip at a time.
- All amounts use one currency. Amounts are plain numbers with two decimal places.
- Equal split is the rule for the first version. Custom shares are optional and come only if time remains.
- Data can live only in the browser for the demo. Keeping it after the browser closes is not required for success.

## Out of Scope
 
- Accounts, sign-in, passwords, and more than one organizer
- A way for friends to open or edit the trip
- Saving several trips and switching between them
- Recording a payer other than the organizer
- Marking a debt as paid, or sending money
- Receipt photos, categories, and more than one currency
- A native phone app
