# Task 1 Project

:::mermaid
sequenceDiagram
    title Hello;
    participant User
    participant .NET UI
    participant Named PIPE
    participant Python Logic
    participant SQLLite Database
    User ->> .NET UI: Press "Create" Button
    note left of .NET UI : Create New Empty order
    .NET UI ->> User : Respond with load visual
    .NET UI ->> Named PIPE : Request available product
    Named PIPE ->> Python Logic : Request available product
    Python Logic ->> SQLLite Database : Search for product information
    SQLLite Database ->> Python Logic : Return product information
    Python Logic ->> Named PIPE : availability response:
    Named PIPE ->> .NET UI : availability response:
    .NET UI ->> User : Create entry fields for input
    User ->> .NET UI : Select Options.
    
:::