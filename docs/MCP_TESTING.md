# Testing MCP Integration with Ansible

## Overview

This document describes how to test the Model Context Protocol (MCP) integration in the Fin Officer application using Ansible playbooks. The tests verify that the MCP server is properly configured, resources and tools are accessible, and the auto-reply functionality works as expected.

## Prerequisites

- Python 3.9 or newer
- Ansible 2.9 or newer
- Running instance of the Fin Officer application
- Updated dependencies with MCP 1.10.0 or newer

## Setup

1. Install the required dependencies:

```bash
pip install -r requirements.txt
```

2. Configure environment variables in `.env` file (you can copy from `.env.example`):

```bash
cp .env.example .env
```

3. Start the application with MCP server:

```bash
python app/mcp_integration.py
```

## Running the Tests

### Full Test Suite

To run all MCP tests:

```bash
cd ansible
ansible-playbook mcp_tests.yml
```

### Specific Test Tags

You can run specific test scenarios using tags:

```bash
# Test only auto-reply functionality
ansible-playbook mcp_tests.yml --tags mcp_auto_reply

# Test only MCP resources
ansible-playbook mcp_tests.yml --tags mcp_resources

# Test only MCP tools
ansible-playbook mcp_tests.yml --tags mcp_tools

# Test only email reply prompt
ansible-playbook mcp_tests.yml --tags mcp_prompt
```

## Test Scenarios

### MCP Auto-Reply

Tests the `/api/emails/process-mcp` endpoint which uses MCP to generate an auto-reply to an email. The test verifies that:

1. The endpoint returns a 200 status code
2. The generated reply contains the company name
3. The tone analysis is included in the response

### MCP Resources

Tests the `/api/mcp/resources` endpoint which lists all available MCP resources. The test verifies that:

1. The endpoint returns a 200 status code
2. The resources list is not empty

### MCP Tools

Tests the `/api/mcp/tools` endpoint which lists all available MCP tools. The test verifies that:

1. The endpoint returns a 200 status code
2. The tools list is not empty

### Email Reply Prompt

Tests the `/api/prompts/email-reply` endpoint which generates a prompt for email replies. The test verifies that:

1. The endpoint returns a 200 status code
2. The generated prompt contains the sender name

## Troubleshooting

### Common Issues

1. **Application not running**
   - Ensure the application is running before executing the tests
   - Check the health endpoint at `/health`

2. **MCP server not mounted**
   - Verify that the MCP server is properly mounted at the configured path
   - Check the `MCP_MOUNT_PATH` environment variable

3. **Dependency issues**
   - Make sure you have the latest version of MCP installed
   - Check for any conflicting dependencies

### Logs

To get more detailed logs during testing, set the `LOG_LEVEL` environment variable to `DEBUG` in your `.env` file:

```
LOG_LEVEL=DEBUG
```

## Extending the Tests

To add new test scenarios:

1. Open the `ansible/mcp_tests.yml` file
2. Add a new task block following the existing pattern
3. Add appropriate assertions to verify the expected behavior
4. Add a new tag for the scenario
5. Update the summary section to include the new test result

## Continuous Integration

These tests can be integrated into a CI/CD pipeline by adding the following steps to your workflow:

```yaml
- name: Install dependencies
  run: pip install -r requirements.txt

- name: Start application
  run: python app/mcp_integration.py &
  env:
    MCP_SERVER_NAME: "Fin Officer MCP"
    MCP_COMPANY_NAME: "Fin Officer"
    # Add other environment variables as needed

- name: Wait for application to start
  run: sleep 5

- name: Run MCP tests
  run: cd ansible && ansible-playbook mcp_tests.yml
```
