# Email Processing Flow with MCP and TinyLLM

## ASCII Diagram

```
+----------------+     +----------------+     +----------------+
|                |     |                |     |                |
|  Email Ingress | --> | MCP Processing | --> | SQL Storage    |
|  Service       |     | Services       |     | & Archiving    |
|                |     |                |     |                |
+----------------+     +----------------+     +----------------+
                              |
                              | Parallel Processing
                              v
+----------------+     +----------------+     +----------------+
|                |     |                |     |                |
| Spam Detection | <-- | Attachment    | --> | Auto-Reply     |
| MCP Service    |     | Processing    |     | Generation     |
|                |     | MCP Service   |     | MCP Service    |
+----------------+     +----------------+     +----------------+
                              |
                              | Filtered Attachments
                              v
                       +----------------+
                       |                |
                       | Attachment     |
                       | Storage        |
                       |                |
                       +----------------+
```

## Mermaid Diagram

```mermaid
graph TD
    A[Email Ingress Service] --> B[MCP Processing Services]
    B --> C[SQL Storage & Archiving]
    
    B --> D[Spam Detection MCP Service]
    B --> E[Attachment Processing MCP Service]
    B --> F[Auto-Reply Generation MCP Service]
    
    E --> G[Attachment Filtering]
    G -->|Valid Attachments| H[Attachment Storage]
    G -->|Rejected Attachments| I[Rejection Log]
    
    D -->|Spam Score| J[Spam Classification]
    J -->|Spam| K[Spam Folder]
    J -->|Not Spam| F
    
    F --> L[Reply Generation]
    L --> M[Email Sending Service]
    
    subgraph "TinyLLM MCP Services"
        D
        F
        N[Content Analysis MCP Service]
    end
    
    B --> N
    N --> C
```

## Process Flow Description

1. **Email Ingress**: Incoming emails are received and parsed
2. **MCP Processing**: Multiple MCP services process the email in parallel:
   - **Spam Detection**: Evaluates if the email is spam
   - **Attachment Processing**: Filters and processes attachments
   - **Content Analysis**: Analyzes email content for sentiment, urgency, etc.
   - **Auto-Reply Generation**: Creates appropriate responses
3. **Attachment Filtering**:
   - Rejects attachments > 10MB
   - Blocks specific extensions (.tar, .doc, etc.)
   - Scans for malware/suspicious content
4. **SQL Storage**: Emails and metadata are stored in SQL database
5. **Auto-Reply**: Generated responses are sent back to the sender
