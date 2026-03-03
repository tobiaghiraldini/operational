# Operational software requirements specifications
Operational is a management, knowledge base and monitoring dashboard, intended to cover every need of my (any) company.

## Web Stack
Django, Celery, Tailwind, Htmx, React
## iOS Stack
SwiftUI, SwiftData, 
## MacOS Stack
## Languages
python, html, htmx, css, ts, yaml, Swift, SwiftUI
## Architecture

## Modules

### Core - the core of operational, its workflows, algorithm...
where high level architecture, orchestration, highly reused or project wide functionalities live

### Customers - everyone can use this, and their data should be safe
multi tenant SaaS support with common shared data and tenant private data, achieved through postgres schemas. one tenant per schema, plus a shared schema.

### Subscriptions, authentication, authorization - 
role based access, with levels of subscription that determine which features users have access to.

### AI - we can't live without ai anymore
ai-human interface, mcp infrastructure, machine learning with local data

### API - the rest api for the rest of the world, and for the rest of the operational clients
rest api to connect other operational clients, and provide customers to an api endpoint for their integrations with operational

### Services - 
external services where external api keys are created, and need to managed.

### Integrations - external services integrated
api clients, all the integrations with external systems will live here

### Dashboard
a customizable dashboard to monitor and reach all the needed features at a glance

### Plan - improvisation kills outcomes
Plans are made of milestones, and maybe of other things

### Milestone -
set your goal with dates, details, tasks and other info

### Products - projects or other types of products that can be created. 
Products are made of plans, milestones, systems, and parts (and other). Their status can be live, dev, testing. they can have api keys and other sensible information that need to be traced in a safe manner, and tracked to highlight deadlines, due dates, expirations, rotations needed.

### Systems - once you create a complex system, make it worth it and reusable. 
Systems are made of parts.
- infrastructure
- multi tenant system
- authentication system
- permissions system
- background tasks system
- observability system
- api client system
- mcp server system

### Parts - every small part deserve its own space and tracing. every token, account, api key which is part of something needs to be tracked and acknowledged

### Topics - main concepts that define knowledge, products parts, systems and anything that is worth to be part of a topic
Topics relate to almost everything in here.

### Knowledge - don't lose your mind, don't lose any knowledge. everything is made of something. track how everything is done and related to the other parts (systems, products, knowledge, ...)
all the knowledge should be mapped with a node graph (like react-flow) to show what everything is made of and connect to (like a projects made of parts and systems, all of which can relate to topics and everything that is connected. then from any part of the graph it should be possible to explore other connected areas of knowledge)

### Tasks - get sh!t done and organized

### Deadlines - deadlines with status check. don't forget, don't do twice (for anything that makes sense like products, plans, payments, expiring tokens or accounts)

### Money - expenses and earnings, budgets, trends, graphs

### Accounting - tax reporting tool
the features that ease your tax reporting to your accountant or to the tax authorities:
- journal entries
- financial statements
- monthly/quarterly/annual reports
- cash flow
- bank account movements
- more....

