# Nexavo Billing System

Nexavo Billing System is a Django-based ISP Operations Support System (OSS) developed to automate customer management, billing, payment processing, and network service activation for Internet Service Providers.

The project is being built with a strong focus on automation, reliability, and scalability while serving as the foundation for future ISP management solutions.

---

## Current Features

### Client Management

* Client registration and management
* Account number generation
* Customer wallet system

### Subscription Management

* Internet package management
* Subscription lifecycle management
* Automatic renewals
* Invoice generation

### Billing Engine

* Automated billing
* Wallet deductions
* Scheduled billing using Cron
* Transaction logging

### M-Pesa Integration

* Daraja Paybill Callback
* STK Push Initiation
* STK Push Callback
* Duplicate transaction protection
* Wallet crediting

### SMS Integration

* Africa's Talking SMS
* Payment confirmations
* Renewal reminders
* Notification logging

### MikroTik Automation

* PPP Secret Enable/Disable
* Disconnect Active Sessions
* Billing automation
* MikroTik logging

### System Logging

* Billing logs
* M-Pesa logs
* SMS logs
* MikroTik logs

---

## Technology Stack

* Python
* Django
* SQLite (Development)
* MikroTik RouterOS API
* Safaricom Daraja API
* Africa's Talking API
* Cron

---

## Current Version

**v0.3.0**

---

## Roadmap

* Customer Self-Service Portal
* PostgreSQL Migration
* VPS Deployment
* Nginx + Gunicorn
* SSL (Let's Encrypt)
* Multi-router Support
* Hotspot Management
* RADIUS Integration

---

## Vision

Nexavo aims to become a complete ISP Operations Support System that enables Internet Service Providers to automate customer onboarding, billing, payments, network provisioning, and service monitoring through a unified platform.
