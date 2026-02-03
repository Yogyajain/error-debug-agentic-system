
from agents.parent_agents import graph_final
from agents.helper import chain_log_parser,chain_error_detector
def create_sample_logs():
    """Create sample log files for demonstration"""
    
    web_server_log = """
[2024-01-29 10:23:45] ERROR: HTTP 500 - Internal Server Error at /api/users
[2024-01-29 10:23:46] ERROR: Database connection failed - Connection timeout after 30s
[2024-01-29 10:23:47] ERROR: Unable to serve request /api/users - Database unavailable
[2024-01-29 10:24:10] WARNING: High memory usage: 87%
[2024-01-29 10:24:12] INFO: Attempting database reconnection...
[2024-01-29 10:24:15] ERROR: Database connection failed - Connection timeout after 30s
[2024-01-29 10:25:01] ERROR: HTTP 500 - Internal Server Error at /api/products
[2024-01-29 10:25:02] ERROR: Unable to serve request /api/products - Database unavailable
[2024-01-29 10:25:30] ERROR: Database connection failed - Connection timeout after 30s
[2024-01-29 10:26:45] WARNING: Connection pool exhausted - 50/50 connections in use
[2024-01-29 10:27:12] ERROR: Database connection failed - Connection timeout after 30s
[2024-01-29 10:30:15] INFO: Database connection restored
[2024-01-29 10:30:16] INFO: Connection pool status: 15/50 connections in use
[2024-01-29 10:30:17] INFO: Server operating normally
    """
    
    application_log = """
[2024-01-29 10:15:23] INFO: Application started successfully on port 8080
[2024-01-29 10:15:24] INFO: Connected to database: postgresql://prod-db:5432
[2024-01-29 10:23:44] ERROR: NullPointerException in UserService
[2024-01-29 10:23:44] ERROR: Stack trace: at com.example.UserService.getUser(UserService.java:156)
[2024-01-29 10:23:44] ERROR: Caused by: User object is null for ID: 12345
[2024-01-29 10:24:10] WARNING: Deprecated API call detected: /v1/legacy/endpoint
[2024-01-29 10:24:11] WARNING: Client using outdated API version 1.0
[2024-01-29 10:25:00] ERROR: NullPointerException in UserService
[2024-01-29 10:25:00] ERROR: Stack trace: at com.example.UserService.getUser(UserService.java:156)
[2024-01-29 10:25:00] ERROR: Caused by: User object is null for ID: 67890
[2024-01-29 10:26:33] ERROR: NullPointerException in UserService
[2024-01-29 10:26:33] ERROR: Stack trace: at com.example.UserService.getUser(UserService.java:156)
[2024-01-29 10:26:33] ERROR: Caused by: User object is null for ID: 11223
[2024-01-29 10:28:05] INFO: Cache hit rate: 45%
[2024-01-29 10:28:06] WARNING: Cache performance below threshold (target: 80%)
[2024-01-29 10:30:00] INFO: Hourly metrics: 1500 requests, 150 errors, 10% error rate
    """
    
    database_log = """
[2024-01-29 10:20:15] INFO: Database server started on port 5432
[2024-01-29 10:20:16] INFO: Ready to accept connections
[2024-01-29 10:23:40] WARNING: Query execution time exceeded threshold: 15.3s
[2024-01-29 10:23:40] WARNING: Slow query: SELECT * FROM users WHERE status='active'
[2024-01-29 10:23:41] ERROR: Connection pool exhausted - rejecting new connections
[2024-01-29 10:23:42] ERROR: Too many open connections: 105/100
[2024-01-29 10:24:15] WARNING: Query execution time exceeded threshold: 18.7s
[2024-01-29 10:24:15] WARNING: Slow query: SELECT * FROM orders JOIN users ON...
[2024-01-29 10:24:50] ERROR: Connection pool exhausted - rejecting new connections
[2024-01-29 10:25:10] ERROR: Deadlock detected between transactions T1 and T2
[2024-01-29 10:25:10] ERROR: Rolling back transaction T2
[2024-01-29 10:26:30] WARNING: Index missing on users.status column
[2024-01-29 10:26:30] WARNING: Query planner performing full table scan
[2024-01-29 10:29:00] INFO: Connection pool reconfigured: max_connections=150
[2024-01-29 10:30:15] INFO: Connection pool status: 45/150 connections active
    """
    
    return [
        {
            'name': 'web_server.log',
            'type': 'web_server',
            'content': web_server_log
        },
        {
            'name': 'application.log',
            'type': 'application',
            'content': application_log
        },
        {
            'name': 'database.log',
            'type': 'database',
            'content': database_log
        }
    ]

# res = graph_final.invoke({
#     "log_files": create_sample_logs()
# })

res1=chain_log_parser.invoke({"raw_log_file": create_sample_logs()[0]['content']})
res=chain_error_detector.invoke({"parsed_log_json": res1})
print("Final Result:", res)