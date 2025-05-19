#!/bin/bash

# Script to run Ansible tests for Email LLM Processor

set -e

CURRENT_DIR=$(pwd)
SCRIPT_DIR=$(dirname "$0")
cd "$SCRIPT_DIR"

echo "=== Email LLM Processor - Ansible Tests ==="
echo ""

# Check if Ansible is installed
if ! command -v ansible-playbook &> /dev/null; then
    echo "Installing Ansible..."

    # Install Ansible based on the detected OS
    if command -v apt-get &> /dev/null; then
        sudo apt-get update
        sudo apt-get install -y ansible
    elif command -v yum &> /dev/null; then
        if grep -q 'Fedora' /etc/os-release; then
            sudo dnf install -y ansible
        else
            sudo yum install -y epel-release
            sudo yum install -y ansible
        fi
    elif command -v brew &> /dev/null; then
        brew install ansible
    elif command -v pip3 &> /dev/null; then
        pip3 install --user ansible
    elif command -v pip &> /dev/null; then
        pip install --user ansible
    else
        echo "Error: Could not install Ansible automatically."
        echo "Please install Ansible manually and try again."
        echo "Visit: https://docs.ansible.com/ansible/latest/installation_guide/intro_installation.html"
        exit 1
    fi

    echo "Ansible installed successfully."
fi

# Check if application is running
if ! curl -s http://localhost:8000/health > /dev/null; then
    echo "Warning: The Email LLM Processor application doesn't seem to be running."
    echo "Make sure to start it with 'docker-compose up -d' before running tests."
    echo ""
    read -p "Do you want to continue anyway? (y/n): " continue_anyway
    if [[ "$continue_anyway" != "y" ]]; then
        exit 1
    fi
fi

# Parse command line arguments
if [ "$1" == "--help" ] || [ "$1" == "-h" ]; then
    echo "Usage: $0 [options] [test_playbook] [--tags tag1,tag2]"
    echo ""
    echo "Options:"
    echo "  --help, -h     Show this help message"
    echo "  --verbose, -v  Run with verbose output"
    echo "  --list         List available test playbooks"
    echo ""
    echo "Available test playbooks:"
    echo "  main.yml               - Run all tests"
    echo "  email_tests.yml        - Basic email functionality tests"
    echo "  email_service_tests.yml - Email service specific tests"
    echo "  email_scenarios_tests.yml - Various email scenario tests"
    echo ""
    echo "Examples:"
    echo "  $0                     # Run all tests"
    echo "  $0 email_tests.yml     # Run only basic email tests"
    echo "  $0 email_scenarios_tests.yml --tags standard_email,urgent_email"
    exit 0
fi

if [ "$1" == "--list" ]; then
    echo "Available test playbooks:"
    echo "  main.yml"
    echo "  email_tests.yml"
    echo "  email_service_tests.yml"
    echo "  email_scenarios_tests.yml"
    exit 0
fi

VERBOSE=""
if [ "$1" == "--verbose" ] || [ "$1" == "-v" ]; then
    VERBOSE="-v"
    shift
fi

# Determine which playbook to run
PLAYBOOK="main.yml"
if [ -n "$1" ] && [ -f "$1" ]; then
    PLAYBOOK="$1"
    shift
fi

# Run the playbook
echo "Running playbook: $PLAYBOOK"
echo ""

ANSIBLE_ARGS="$VERBOSE $@"
ansible-playbook "$PLAYBOOK" $ANSIBLE_ARGS

EXIT_CODE=$?

echo ""
if [ $EXIT_CODE -eq 0 ]; then
    echo "✅ Tests completed successfully!"
else
    echo "❌ Tests failed with exit code $EXIT_CODE"
fi

# Return to original directory
cd "$CURRENT_DIR"

exit $EXIT_CODE
