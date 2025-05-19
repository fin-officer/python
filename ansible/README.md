# Email LLM Processor - Ansible Tests

This directory contains Ansible playbooks for testing the Email LLM Processor application, with a focus on email functionality.

## Prerequisites

- Ansible 2.9 or higher installed
- The Email LLM Processor application running (via Docker Compose)
- Python 3.x with the `ansible` and `docker` Python packages installed

## Test Structure

The test suite is organized into several playbooks:

- `main.yml` - The main entry point that runs all tests
- `email_tests.yml` - Basic tests for email functionality
- `email_service_tests.yml` - Tests focused on the email service component
- `email_scenarios_tests.yml` - Tests for various email scenarios (urgent, negative feedback, etc.)

## Running the Tests

To run all tests:

```bash
cd /home/tom/github/fin-officer/python/ansible
ansible-playbook main.yml
```

To run specific test playbooks:

```bash
ansible-playbook email_tests.yml
ansible-playbook email_service_tests.yml
ansible-playbook email_scenarios_tests.yml
```

To run specific test scenarios using tags:

```bash
ansible-playbook email_scenarios_tests.yml --tags "standard_email,urgent_email"
```

## Test Environment

The tests are configured to run against the local Docker environment where the Email LLM Processor application is deployed. The tests assume the following services are running:

- FastAPI application on http://localhost:8000
- MailHog (test email server) on http://localhost:8025

## Test Results

Test results will be displayed in the console output. Each test will report whether it passed or failed, and a summary will be provided at the end of each playbook run.

## Troubleshooting

If tests are failing, check the following:

1. Ensure the application is running (`docker-compose ps`)
2. Check application logs for errors (`docker-compose logs app`)
3. Verify MailHog is accessible at http://localhost:8025
4. Check network connectivity between Ansible and the Docker containers

## Extending the Tests

To add new test scenarios:

1. Edit the appropriate playbook or create a new one
2. Add new tasks following the existing patterns
3. Use tags to categorize your tests
4. Update the main playbook if you've created a new test file
