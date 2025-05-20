#!/bin/bash

# Colors for output
GREEN="\033[0;32m"
RED="\033[0;31m"
YELLOW="\033[0;33m"
BLUE="\033[0;34m"
NC="\033[0m" # No Color

echo -e "${BLUE}=== Testing Auto-Reply Functionality with MCP ===${NC}\n"

# Step 1: Check if the API is running
echo -e "${YELLOW}Checking if API is running...${NC}"
API_STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/health)

if [ "$API_STATUS" -eq 200 ]; then
    echo -e "${GREEN}✅ API is running (status code: $API_STATUS)${NC}"
else
    echo -e "${RED}❌ API is not running (status code: $API_STATUS)${NC}"
    echo -e "${YELLOW}Please make sure the application is running in Docker${NC}"
    exit 1
fi

# Step 2: Create a test email
echo -e "\n${YELLOW}Creating a test email...${NC}"
CREATE_EMAIL_RESPONSE=$(curl -s -X POST http://localhost:8000/api/emails/process \
    -H "Content-Type: application/json" \
    -d '{"from_email":"test@example.com","to_email":"support@finofficer.com","subject":"Question about financial services","content":"Hello,\n\nI am interested in your financial services. Could you please provide more information about your accounting packages for small businesses? I currently have 5 employees and need help with monthly bookkeeping and tax filing.\n\nThank you,\nJohn","received_date":"'$(date -Iseconds)'"}' \
    -w "\n%{http_code}")

HTTP_CODE=$(echo "$CREATE_EMAIL_RESPONSE" | tail -n1)
RESPONSE_BODY=$(echo "$CREATE_EMAIL_RESPONSE" | sed '$d')

if [ "$HTTP_CODE" -eq 200 ]; then
    echo -e "${GREEN}✅ Test email created successfully${NC}"
    echo -e "${BLUE}Response: $RESPONSE_BODY${NC}"
else
    echo -e "${RED}❌ Failed to create test email (status code: $HTTP_CODE)${NC}"
    echo -e "${RED}Response: $RESPONSE_BODY${NC}"
    exit 1
fi

# Step 3: Get the email ID (for simplicity, we'll use ID 1)
EMAIL_ID=1
echo -e "\n${YELLOW}Using email ID: $EMAIL_ID${NC}"

# Step 4: Test the auto-reply functionality
echo -e "\n${YELLOW}Testing auto-reply for email ID $EMAIL_ID...${NC}"
AUTO_REPLY_RESPONSE=$(curl -s -X POST http://localhost:8000/api/emails/$EMAIL_ID/auto-reply \
    -H "Content-Type: application/json" \
    -w "\n%{http_code}")

HTTP_CODE=$(echo "$AUTO_REPLY_RESPONSE" | tail -n1)
RESPONSE_BODY=$(echo "$AUTO_REPLY_RESPONSE" | sed '$d')

if [ "$HTTP_CODE" -eq 200 ]; then
    echo -e "${GREEN}✅ Auto-reply generated successfully${NC}"
    
    # Extract the content from the JSON response
    CONTENT=$(echo $RESPONSE_BODY | python3 -c "import sys, json; print(json.load(sys.stdin).get('content', ''))")
    STATUS=$(echo $RESPONSE_BODY | python3 -c "import sys, json; print(json.load(sys.stdin).get('status', ''))")
    MESSAGE=$(echo $RESPONSE_BODY | python3 -c "import sys, json; print(json.load(sys.stdin).get('message', ''))")
    
    echo -e "${BLUE}Status: $STATUS${NC}"
    echo -e "${BLUE}Message: $MESSAGE${NC}"
    echo -e "\n${YELLOW}Auto-reply content:${NC}"
    echo -e "$CONTENT"
else
    echo -e "${RED}❌ Failed to generate auto-reply (status code: $HTTP_CODE)${NC}"
    echo -e "${RED}Response: $RESPONSE_BODY${NC}"
    exit 1
fi

echo -e "\n${GREEN}✅ All tests passed successfully!${NC}"
