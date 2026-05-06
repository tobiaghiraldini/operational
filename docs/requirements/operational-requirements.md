# Operational software requirements specifications

Operational is an application that aim to manage the entire small corporates operations. it's intended to cover every need of my (any) company.

## Web Stack

Django, Celery, Tailwind, Htmx, React, React flow, langchain, deepagents, ollama

## iOS Stack

SwiftUI, SwiftData, TBD

## MacOS Stack

TBD

## Languages

WEB: python, html, htmx, css, ts, yaml  
iOS: Swift, SwiftUI

## Architecture

Multi tenancy architecture with single database and multiple schemas.

Background workers based on celery and redis to offload long running, scheduled and heavy tasks.

Integrations layer for external apis and providers

Stripe subscriptions

## Main areas

- planning: gantt, roadmaps, milestones/sprints planning, operations planning
- customers and vendors: contacts that are used through projects, finances
- project management: projects, milestones, tasks, systems, parts, services, architectures, solutions
- product management: built projects, feedbacks, users, spendings, infrastructures
- service management: tokens, api key, auths, integrations
- operations: maintenance, status, keys rotations, security audit, monitoring
- knowledge base: topics, patterns, libs, frameworks, languages, problems' solutions, cheatsheets, procedures
- finance: spending and earnings, invoices management (incoming, outgoing, trends), budgets, costs monitoring for active services
- accounting: reports, files and economics to prepare for the accounting regulations (regulations vary per country, on a multi tenant system these regulations should be dynamic)
- ai agents: agents that are aware and can operate along with the users to varying degrees (knowledge base, operations assistant, security supervisor)
- api: rest apis with auth and quotas for customers
- mcp: server and client to expose operational agentic workflow and data through mcp and to connect to third parties mcps.

## Modules

### Core - the core of Operational, its workflows, algorithms, orchestrations

where high level architecture, orchestration, highly reused or project wide functionalities live

### Tenants, Users - Operational tenants, domains and tenants users, with their data safe and private

Tenancy Clients/organizations and Domains. support to common features (organizations can have many tenant users, ...) with shared data and tenant private data, achieved through postgres schemas. one tenant per schema, plus a shared schema.

### Subscriptions, authentication, authorization

Signin, Signup with levels of subscriptions that determine which features users have access to.

invite other users to own organization. users roles within organizations.

super admin role that can impersonate other tenants.

oauth with selected providers.

### AI - we can't live without ai anymore

ai-human interface, mcp infrastructure, machine learning with local data, local agentic workflow allows users to automate their processes.

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

