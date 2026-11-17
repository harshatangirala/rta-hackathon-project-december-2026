# DemandPulse Explained Simply

A plain-language guide to everything Team 7 built for the RTA Future Move Hackathon, written so anyone can follow it and explain it back. November 2026.

## The whole project in one minute

Imagine you run Dubai's buses. Some buses are packed while others drive around almost empty, and some buses keep getting stuck. We built a tool that finds these problems and suggests fixes.

It does four jobs:

1. **Predicts** how many people will board each bus route in the next 15 minutes and the next hour.
2. **Spots mismatches:** hours where a route has more passengers than seats, and hours where big buses run nearly empty.
3. **Finds traffic hotspots:** stretches of road between two stops where buses lose the most time, and how many passengers suffer.
4. **Writes action cards with AI**, then checks them with a fact-checker program before a human approves anything.

We built all of it in **Dataiku**, a tool where you connect data steps like boxes on a map. The results appear on two dashboards (small websites inside Dataiku) for RTA staff.

**The three numbers to remember:**

- Our 15-minute prediction is **18.3% more accurate** than the simple guess.
- Swapping **18 buses** between quiet and busy routes moves **792 seats** and fixes **13 of 28** overcrowded hours, without cancelling a single trip (on paper).
- The AI wrote **24 answers** and the fact-checker passed **all 24**.

## The four data files, explained like notebooks

Think of each dataset as a notebook that someone kept.

| Notebook | What is written in it | How big | Which day |
| --- | --- | --- | --- |
| **Nol card taps** | Every time someone tapped their Nol card getting on (check-in) or off (check-out) a bus | 1,056,343 taps | Real, Monday 15 Dec 2025 |
| **Running times** | For every bus trip at every stop: when it was supposed to leave and when it actually left | 259,435 rows | Real, the same Monday |
| **Fleet list** | Every vehicle, its type and how many people it can carry | 3,264 vehicles | A reference list |
| **Stops** | Each stop's name and its location on the map | 2,607 stops matched | From the *planned* 2026 timetable |

**Two important rules we followed:**

- **Real vs planned:** the taps and running times are what really happened in 2025. The stops file comes from a 2026 *plan*. We only used it to put dots on a map, never to compare 2025 with 2026.
- **Privacy:** each Nol card has an ID number, and each driver has one too. We removed those ID columns from our working copies in the very first cleaning step; the original files stay untouched. Nobody can be identified in any of our results, and the AI never sees personal data.

## Words you need to know

| Word | What it means in simple terms | Example from our project |
| --- | --- | --- |
| **Route** | A bus line with a code | F27, 11CUP, C01 |
| **Boarding** | One person getting on a bus (a card check-in) | 138 boardings on route 11CUP at 17:00 |
| **Slot** | A 15-minute block of the day; a day has 96 of them | 18:00-18:15 is one slot |
| **Route-hour** | One route during one hour | Route C01 between 04:00 and 05:00 |
| **Demand pressure** | Boardings divided by seats offered in that hour. Above 1.0 means more taps than seats | 138 people / 69 seats = 2.00 |
| **Forecast** | A prediction of a number in the future | Boardings on a route 15 minutes from now |
| **Baseline** | The simple guess we must beat: "the next 15 minutes will look like the last known 15 minutes" | If 40 people boarded at 17:00-17:15, guess 40 for 17:15-17:30 |
| **Lag** | The value from an earlier slot. Lag 1 = one slot ago, lag 4 = one hour ago | Boardings 4 slots ago |
| **Training data / test data** | The model learns from the morning (training) and is graded on the evening it never saw (test) | Learn 02:00-13:59, test 14:00-23:59 |
| **Leakage** | Accidentally letting the model see the answer, like a student seeing the exam answers | Our first try did this and we threw it away |
| **MAE** | Mean Absolute Error: on average, how many people the prediction is off by | MAE 16.68 = off by about 17 people per route per slot |
| **RMSE** | Like MAE, but big mistakes count extra | 23.79 at 15 minutes |
| **WAPE** | Total error as a percentage of total passengers | 30.9% |
| **MAPE** | Average percentage error per row; jumps around when numbers are small | 47.5% |
| **R2** | How much of the ups and downs the model explains: 1.0 is perfect, 0 is useless | 0.76 for the 15-minute model |
| **Ridge, Random forest, XGBoost** | Three types of prediction models. Ridge is a straight-line formula; the other two use many decision trees | Ridge won |
| **Hotspot** | A stretch between two stops where buses run 30 seconds or more behind schedule | Max Metro to Satwa on F27 |
| **Passenger-delay minutes** | People boarding at the start of a slow stretch x the minutes lost | 12,046 minutes on F27 |
| **LLM / AI agent** | A language model (like a chatbot) given a job and a role | The supply-demand specialist |
| **Prompt** | The written instructions we give the AI | "Use only these facts, write 4 lines" |
| **Guardrail** | A rule the solution must never break | No fare increase, no trip cut |
| **Flow, zone, recipe** | In Dataiku: the Flow is the whole map of steps, a zone is a coloured group, a recipe is one step that turns data into new data | The Group recipe that counts boardings |
| **Webapp** | A small website built inside Dataiku | DemandPulse Ops |

## What we built, step by step

Our Dataiku Flow is like a factory line with 7 rooms (zones). Data enters on the left and finished answers come out on the right. In total it has 39 datasets, 30 recipes and 2 trained models.

1. **Source Data (red room):** the four notebooks come in. We never change the originals.
2. **Data Cleaning & Quality (purple room):** we remove card and driver IDs, fix the time columns and count rows by date and route. That proves all data is from one day. We found small problems and handled each one:
    - 106 taps (0.01%) had no route, so we left them out.
    - 11,098 running-time rows (4.3%) had no delay value, so we skipped them for delay maths.
    - 619 vehicles (19%) had capacity 0, which is impossible, so we treated it as "unknown".
    - One bus number (3100) appeared twice, so we kept one row per bus.
3. **Demand Aggregation & Preparation (blue room):** we put every tap into its 15-minute slot and counted boardings per route per slot. Then we built a full table of 117 routes x 96 slots and wrote 0 where nobody boarded. Why? A model that looks at "the last slot" must never skip quiet slots by mistake.
4. **Forecasting & Evaluation (teal room):** we created lag columns (what happened 1, 2, ... 8 slots ago), split morning from evening, trained three models per time horizon and graded them against the simple guess.
5. **Fleet & Route Operations (dark purple room):** for each route-hour we counted how many seats were offered (trips x bus size) and compared it to boardings. This gives demand pressure, late-bus flags and the bus-swap idea.
6. **Crowding & Operational Reporting (yellow room):** we worked out where buses lose time between two stops, which stops are crowded, whether another route could help, and a daily report of 16 actions.
7. **AI Decision Support (orange room):** we turned the top 12 problems into short fact sheets. AI agents wrote action cards from them, and a checker program verified every card.

Most steps (25 of 30) use Dataiku's no-code "visual recipes", as the hackathon guide asks. We wrote Python code only for 5 jobs that are hard to click together: grading the forecast, the decision rules and swap, the road-segment maths, building the AI fact sheets, and checking the AI answers.

## The forecast

Our model predicts how many people will board each of 117 routes in the next 15 minutes, and in 60 minutes. At 15 minutes it is clearly better than the simple guess; at 60 minutes it is only a little better.

### How we made it fair

- **The simple guess (baseline):** "the future equals the last number I know". A real model must beat this, or it is useless.
- **No peeking:** the model learned from 02:00-13:59 and was tested on 14:00-23:59, which it had never seen. That is like studying the morning chapters and being examined on the evening chapters.
- **No cheating columns:** the 60-minute model may only use data from at least one hour before. If it used data from 15 minutes ago, it would be using information it would not have yet.
- **We caught our own mistake:** our first attempt mixed morning and evening rows randomly and used "cheating" columns. It scored amazingly well (error of only about 11 people), which was too good to be true. We threw it away and rebuilt it properly.

### Which model won

We tried three models. Lower MAE is better; higher R2 is better.

| Prediction | Ridge | Random forest | XGBoost |
| --- | --- | --- | --- |
| 15 minutes ahead: MAE | **16.72** | 16.96 | 17.45 |
| 15 minutes ahead: R2 | **0.76** | 0.75 | 0.73 |
| 60 minutes ahead: MAE | **21.39** | 21.96 | 22.07 |
| 60 minutes ahead: R2 | **0.61** | 0.57 | 0.55 |

The simplest model, Ridge, won both times. That happens when the best clue is simply "what just happened on this route", which is exactly what Ridge is good at.

### Worked example: what "18.3% better" means

- On the evening test hours, the simple guess was off by **20.41 people** per route per slot on average.
- Our Ridge model was off by **16.68 people** on average.
- Improvement = (20.41 - 16.68) / 20.41 = 3.73 / 20.41 = about **18.3%**.
- At 60 minutes: 22.73 vs 21.33, so only **6.1%** better.
- In the busy evening peak (16:00-19:59) the 15-minute model is **19.5%** better, which is where it matters most.

### Is the error still big?

Yes. The total error (WAPE) is about 31% at 15 minutes. A route-slot averages about 54 boardings, so being off by about 17 is a lot. That is why we say: use it as an **early warning**, not as an exact head count.

(The small difference between 16.72 in the model table and 16.68 here comes from one rule: if the model predicts a negative number of people, we change it to 0.)

## Crowded buses, empty buses and the bus swap

The network has many more empty hours than crowded ones, so the fix is to move buses around rather than buy new ones.

### Measuring "how full"

For each route and hour we divide boardings by seats offered. We call this **demand pressure**.

- **Example:** route 11CUP at 17:00 had 138 boardings and only 1 trip with a 69-seat bus. 138 / 69 = **2.00**, so twice as many card taps as seats.
- **1.0 or more** = high pressure (we flag it). **0.25 or less** = under-used (a big bus mostly empty).
- It is a **warning signal, not a head count**. People paying cash are missing, and a passenger may ride across two hours. We need passenger counters on buses to confirm.

### What we found

| What | How many route-hours |
| --- | --- |
| Crowded (1.0 or more) | 28 |
| Mostly empty (0.25 or less) | 1,262 |
| Often late (30% or more of buses over 5 minutes late) | 761 |

The crowded hours carry only 1.1% of all boardings, but those passengers have the worst trips. Route C01 is a good example of the wrong bus in the wrong hour: one crowded hour (1.87 at 04:00), 12 nearly empty hours and 9 often-late hours.

### The bus swap (a what-if)

Idea: in the same hour, take a big bus (100+ seats) from a route that is mostly empty and give it to a crowded route that runs a small bus. Give the small bus back the other way. Nothing is cancelled.

- Rule: the route giving away its big bus must stay at 0.50 or less afterwards, so we do not create a new problem.
- Result on paper: **18 swaps, 792 seats moved, 0 trips removed. 13 of the 28 crowded hours drop below 1.0.**
- The other 15 crowded hours need something else, such as an extra standby bus.

This is a calculation, not a real test. RTA would need to try it on a few routes and measure.

## Where buses get stuck: hotspots and alternative routes

One stretch of road stands out: route F27 from Max Metro Bus Stop Landside 2 to Satwa, Masjid 1.

### How we measured it

For every bus trip and every pair of stops next to each other, we compared:

- **Planned time** between the two stops (from the timetable).
- **Actual time** between the two stops (from the bus's real departure times).

If the median bus in an hour takes 30 seconds or more longer than planned, that stretch is a **hotspot**. We then multiplied by the people who boarded at the first stop, to see how many people feel the delay (passenger-delay minutes).

### What we found

- 4,620 stretch-hours checked; **388 (8.4%)** were hotspots.
- **F27, Max Metro to Satwa:** planned 7-8 minutes in the evening, actually about 15-16 minutes. Every single trip ran more than a minute late. Up to 447 people per hour board there, giving 12,046 passenger-delay minutes, ten times the next worst stretch.
- **Route 310 near E311 in the morning:** buses ran 82-97 seconds slow at about 32 km/h instead of the planned 45 km/h. This looks like real traffic.

### Can passengers use another route?

We searched for another route serving the same two stops in the same hour, with spare seats and less delay. Only **1 of the top 30** hotspots had one: route F09 between Satwa Roundabout 2 and Max Metro at 18:00 ran 28 seconds *ahead* of schedule with plenty of room, while F27 on the same stops ran 193.5 seconds late.

### The honest catch

If a bus is slower than the timetable, either the **road is jammed** or the **timetable is unrealistic**. Our data cannot tell which. So our main advice is to review the timetable first, which costs nothing.

## The AI agents: a small team with a fact-checker

Think of the AI part as a small office team. The numbers are already calculated by the Flow; the team's job is to explain them clearly and suggest one action, and a strict fact-checker reads everything before it reaches a manager.

| Team member | What it is in Dataiku | What it does |
| --- | --- | --- |
| **The file clerk** | Python recipe agent_cases | Prepares 12 short fact sheets: the 5 worst road stretches, the 3 most crowded route-hours, 2 nearly empty big-bus hours and the 2 least reliable routes. No personal data. |
| **Specialist 1: congestion and reliability** | Prompt recipe (AI) | Reads the delay fact sheets and explains what they mean for passengers |
| **Specialist 2: supply and demand** | Prompt recipe (AI) | Reads the crowding and empty-bus fact sheets and suggests a capacity step |
| **The coordinator** | Second Prompt recipe (AI) | Combines facts, rule and specialist view into a 4-line card: CHANGE, WHY, MEASURABLE, GUARDRAIL CHECK |
| **The fact-checker** | Python recipe agent_checks | Checks every AI answer: every number must come from the fact sheet, banned advice (fare rises, cutting trips, bus lanes, skipping driver rest...) must not appear, and the 4 lines must be there |

**Result:** the AI wrote 24 answers (12 specialist views + 12 cards) and the fact-checker passed **all 24**. The dashboard shows a card as "AI-written, numbers verified" only when it passed; otherwise it shows "held for human review" and the rule-based suggestion instead.

**Example card the AI wrote:**

- **CHANGE:** Replace the scheduled bus on Route 11CUP at 17:00 with a larger articulated or double-decker bus; keep every trip and frequency unchanged.
- **WHY:** 138 boardings, 1 trip and 69 seats give demand pressure of 2.00, a screening signal, not a confirmed on-board count.
- **MEASURABLE:** Track demand pressure on Route 11CUP at 17:00.
- **GUARDRAIL CHECK:** No fare change, no trip or frequency cut, no new roads or depots; respect driver rest and bus types.

**Why we built it this way:**

- AI models can make up numbers. Our design never lets the AI calculate; it only explains numbers the Flow already produced, and the fact-checker catches any made-up number.
- The fact-checker proves the **numbers** and **banned words**. It cannot prove the **reasoning** is wise. That is why a human must still tick two boxes before approving any action.
- The AI's wording changes a little each time it runs, but the numbers are checked every time.
- The AI model runs through Dataiku's LLM Mesh. It refused a "temperature" setting, so we left that blank.

## The two dashboards

We built two small websites inside Dataiku. **DemandPulse Ops** reads the latest data straight from the Flow; **DemandPulse Team7** is a saved snapshot for planners. Their source code is in the `code/` folder.

### DemandPulse Ops (for the control room)

| Tab | What you see | Why it helps |
| --- | --- | --- |
| Map and hotspots | Stops as dots (bigger = more boardings), slow stretches as red and amber lines, a "Play day" button that replays the day hour by hour, and a ranked list of slow corridors | Shows where and when buses lose time |
| Actions and agents | 16 suggested actions, each with two tick boxes that must be checked before Approve works; four rule-based summaries; the 12 AI cards; the end-of-day report | Stops a single person from making a hasty mistake |
| Supply-demand gaps | Pick any route: a 24-hour colour strip (teal = spare, green = normal, amber = busy, pink = crowded, white dot = often late) and network-wide top lists | Shows which hours need bigger or smaller buses |
| Passenger advisory | Pick a route and hour: how busy it is and whether a nearby hour is calmer | A message idea for RTA's communications team, not a public app |
| Forecast and method | Model vs simple guess, table and bar chart, plus the limits | Shows the prediction is tested honestly |

### DemandPulse Team7 (for planners)

Forecast accuracy with buttons to switch horizon and metric, a route explorer, the bus-swap result (18 swaps, 13 of 28 fixed, 0 trips removed), three recommendation cards and notes on data handling.

## What we tell RTA to do

Four changes, none of which raises a fare, cancels a trip or builds anything new:

1. **Put the right-size bus in the right hour.** Try the bus swaps on two or three routes such as 11CUP and D03, then measure how full the buses are before and after.
2. **Fix the timetable on the worst stretch first.** F27 from Max Metro to Satwa is planned at 7-8 minutes but takes 15-16 in the evening. Either the plan or the road needs attention, and the plan is free to change.
3. **Add buffer time where buses are always late.** 761 route-hours had 30% or more of buses over 5 minutes late; routes 77 and J02 are the worst. Measure the share of late departures afterwards.
4. **Use the 15-minute prediction as an early warning** to send a standby bus before a route gets crowded. Treat the 60-minute prediction only as a rough hint.

Every action in the dashboard needs two human ticks: for example, "a spare bus and a rested driver are available" and "on-board load confirmed".

## What we must not claim

Being honest about limits makes the project stronger with judges. Say these clearly:

- **Only one day of data.** We cannot say anything about weekends, Ramadan, holidays or seasons. Our predictions are for the same day only.
- **The test was the evening of the same day.** The morning rush was only in the training part, so we did not test it.
- **"Demand pressure" is not how full a bus really is.** It is card taps divided by seats. Real counts need passenger counters.
- **The bus swap is a calculation.** It was not tested on real streets.
- **Slow buses can mean traffic or a bad timetable.** We cannot tell which.
- **The prediction does not yet drive the decisions.** The decision rules use what actually happened; the prediction is tested separately and recommended as the next connection to build.
- **The AI checker checks numbers, not wisdom.** A human still approves every action.
- **Some Nol taps may be from boats or trams**, not only buses, because a few stops are marine stations.
- **The end-of-day report is not sent automatically yet.** That needs an administrator to set up a messaging channel in Dataiku.

## Questions judges may ask

**Why only 15 and 60 minutes ahead, not next week?**
We only have one day of data. You cannot learn a weekly pattern from one Monday, so we kept the forecast to the same day.

**Why did the simplest model, Ridge, win?**
The best clue for the next 15 minutes is what just happened on that route. A straight-line formula on recent values captures that well, and the tree models had nothing extra to find.

**How do you know the model is not cheating?**
We split by time (morning to learn, evening to test), and the 60-minute model only sees data at least one hour old. Our first random-split attempt looked better, so we knew it was leaking and we discarded it.

**Is 18.3% better actually useful?**
Yes, for early warnings at 15 minutes, especially in the evening peak (19.5%). But the error is still about 17 people per route per slot, so it supports a dispatcher's decision; it does not replace one.

**What stops the AI from inventing numbers?**
The AI only receives a short fact sheet, and a separate checker program rejects any answer with a number that is not in that sheet. All 24 answers passed. Cards that fail would not be shown.

**Why didn't you build a passenger chatbot for trip planning?**
The hackathon guide asks teams not to build consumer apps (DO #19). We built a passenger advisory panel for RTA staff instead, which suggests a calmer nearby hour.

**How is privacy protected?**
Card and driver IDs are removed in the first cleaning step; the AI only sees route codes, stop names and totals; and no data left Dataiku.

**Why is route F27 the top priority?**
It has 12,046 passenger-delay minutes, ten times the next stretch. The trip is planned at 7-8 minutes but takes 15-16, and up to 447 people per hour board at its first stop.

**What would you do with more time?**
Load several weeks of data, add passenger-counter data, connect the 15-minute forecast to the decision rules, search for alternative routes at nearby stops, automate the daily report, and move the agents to Dataiku's native Agent feature.
