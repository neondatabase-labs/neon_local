# Next.js Test Suite for Neon Local Proxy

This test suite validates Next.js applications working with Neon database platform through Neon Local Proxy. It covers comprehensive database functionality, advanced Next.js features, and various connection methods.

## 📋 Test Suite Overview

The Next.js test suite consists of 5 comprehensive test files that validate different aspects of Next.js database integration:

### 🧪 Test Files

| Test File | Purpose | Features Tested |
|-----------|---------|-----------------|
| `test-nextjs-comprehensive.js` | Basic Next.js database functionality | CRUD operations, user management, content management, sessions |
| `test-nextjs-advanced.js` | Advanced Next.js patterns | API routes, middleware, SSR/SSG, real-time features |
| `test-nextjs-http.js` | HTTP connections via Neon serverless | API route patterns, server-side props, static props |
| `test-nextjs-websocket.js` | WebSocket connections via Neon serverless | Real-time chat, presence, notifications, data sync |
| `test-nextjs-session-mode.js` | Session-specific PostgreSQL features | Temporary tables, prepared statements, cursors, advisory locks |

### 🎯 Test Runner

- `run-nextjs-tests.js` - Orchestrates and executes all test suites with comprehensive reporting

## 🚀 Quick Start

### Prerequisites

- Node.js 16+ installed
- Neon Local Proxy running on localhost:5432
- PostgreSQL databases: `neondb` (transaction mode) and `neondb_session` (session mode)
- Required npm packages: `pg`, `@neondatabase/serverless`, `ws`

### Installation

```bash
# Install dependencies
npm install pg @neondatabase/serverless ws

# Make test files executable
chmod +x *.js
```

### Running Tests

```bash
# Run all Next.js test suites
node run-nextjs-tests.js

# Run individual test suites
node test-nextjs-comprehensive.js
node test-nextjs-advanced.js
node test-nextjs-http.js
node test-nextjs-websocket.js
node test-nextjs-session-mode.js
```

## 📊 Test Coverage

### 🔧 Comprehensive Tests (`test-nextjs-comprehensive.js`)

Tests core Next.js database functionality:

- **Database Connection & Pooling** - Basic connectivity and connection management
- **User Management** - Registration, authentication, profile management
- **Content Management** - Blog posts, CMS functionality, content retrieval
- **Comment System** - Nested comments, approval workflow
- **Session Management** - User sessions, authentication tokens
- **JSON Operations** - JSONB queries, complex data structures
- **Transactions** - Atomic operations, rollback handling
- **Bulk Operations** - High-performance batch processing
- **Complex Queries** - Joins, aggregations, analytics
- **Full-text Search** - PostgreSQL search capabilities
- **Performance Optimization** - Query optimization, concurrent operations
- **Error Handling** - Constraint violations, recovery patterns

### ⚡ Advanced Tests (`test-nextjs-advanced.js`)

Tests advanced Next.js patterns and features:

- **API Route Simulation** - GET, POST, PUT, DELETE patterns
- **Middleware Patterns** - Request logging, analytics tracking
- **SSR Data Fetching** - getServerSideProps patterns
- **SSG Data Generation** - getStaticProps, ISR (Incremental Static Regeneration)
- **Advanced Query Patterns** - Window functions, CTEs, hierarchical queries
- **Neon Serverless Features** - Serverless driver capabilities
- **Real-time Features** - LISTEN/NOTIFY, WebSocket integration
- **Caching Strategies** - Page cache, API cache, session cache
- **Performance Optimizations** - Query optimization, connection pooling
- **Error Handling Patterns** - API error handling, transaction rollbacks

### 🌐 HTTP Tests (`test-nextjs-http.js`)

Tests Next.js with Neon serverless driver via HTTP:

- **HTTP Connection** - Neon serverless HTTP driver setup
- **API Route Patterns** - RESTful API implementations
- **Server-Side Props** - Data fetching for SSR
- **Static Props** - Data fetching for SSG
- **JSON Operations** - Complex JSON/JSONB operations
- **Transaction Patterns** - HTTP-based transactions
- **Performance Optimization** - HTTP connection optimization
- **Error Handling** - HTTP-specific error scenarios

### 🔌 WebSocket Tests (`test-nextjs-websocket.js`)

Tests Next.js with Neon serverless driver via WebSocket:

- **WebSocket Connection** - Neon serverless WebSocket driver
- **Real-time Chat** - Chat application patterns
- **Real-time Messaging** - Message broadcasting
- **Connection Pooling** - WebSocket connection management
- **Presence System** - Online/offline status, typing indicators
- **Notification System** - Real-time notifications
- **Data Synchronization** - Real-time data updates
- **Transaction Handling** - WebSocket-based transactions
- **Performance Testing** - High-frequency operations
- **Error Handling** - WebSocket-specific error scenarios

### 🔄 Session Mode Tests (`test-nextjs-session-mode.js`)

Tests PostgreSQL session-specific features:

- **Session Connections** - Session vs transaction mode comparison
- **Temporary Tables** - Session-scoped temporary data
- **Session Variables** - Application-specific variables
- **Prepared Statements** - Performance optimization
- **Cursors** - Large dataset processing
- **Advisory Locks** - Background job coordination
- **Session Persistence** - Data persistence across transactions
- **Next.js Features** - ISR cache, middleware logging
- **Performance Testing** - Session-specific optimizations
- **Error Handling** - Session-specific error scenarios

## 🏗️ Next.js Application Patterns

### API Routes

The tests simulate common Next.js API route patterns:

```javascript
// GET /api/users
app.get('/api/users', async (req, res) => {
  const users = await sql`
    SELECT id, username, email, profile
    FROM nextjs_users
    WHERE profile->>'role' = ${req.query.role}
    ORDER BY created_at DESC
  `;
  res.json(users);
});

// POST /api/posts
app.post('/api/posts', async (req, res) => {
  const post = await sql`
    INSERT INTO nextjs_posts (title, content, author_id)
    VALUES (${req.body.title}, ${req.body.content}, ${req.user.id})
    RETURNING id, title, created_at
  `;
  res.json(post[0]);
});
```

### Server-Side Rendering (SSR)

```javascript
// pages/dashboard.js
export async function getServerSideProps(context) {
  const [posts, users, analytics] = await Promise.all([
    sql`SELECT * FROM nextjs_posts WHERE published = true LIMIT 10`,
    sql`SELECT * FROM nextjs_users WHERE profile->>'role' = 'admin'`,
    sql`SELECT COUNT(*) as total FROM nextjs_analytics WHERE created_at > NOW() - INTERVAL '24 hours'`
  ]);

  return {
    props: {
      posts,
      users,
      analytics: analytics[0]
    }
  };
}
```

### Static Site Generation (SSG)

```javascript
// pages/blog/[slug].js
export async function getStaticProps({ params }) {
  const post = await sql`
    SELECT p.*, u.username as author
    FROM nextjs_posts p
    JOIN nextjs_users u ON p.author_id = u.id
    WHERE p.slug = ${params.slug} AND p.published = true
  `;

  return {
    props: { post: post[0] },
    revalidate: 3600 // ISR: regenerate every hour
  };
}

export async function getStaticPaths() {
  const posts = await sql`
    SELECT slug FROM nextjs_posts WHERE published = true
  `;

  return {
    paths: posts.map(post => ({ params: { slug: post.slug } })),
    fallback: 'blocking'
  };
}
```

### Middleware

```javascript
// middleware.js
import { NextResponse } from 'next/server';

export function middleware(request) {
  // Log request for analytics
  const logData = {
    path: request.nextUrl.pathname,
    method: request.method,
    userAgent: request.headers.get('user-agent'),
    timestamp: new Date().toISOString()
  };

  // In real app, this would be logged to database
  console.log('Request logged:', logData);

  return NextResponse.next();
}
```

## 🔧 Database Schema

### Core Tables

```sql
-- Users table for authentication and profiles
CREATE TABLE nextjs_users (
  id SERIAL PRIMARY KEY,
  username VARCHAR(50) UNIQUE NOT NULL,
  email VARCHAR(100) UNIQUE NOT NULL,
  full_name VARCHAR(100),
  avatar_url TEXT,
  bio TEXT,
  settings JSONB DEFAULT '{}',
  is_active BOOLEAN DEFAULT true,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Posts table for content management
CREATE TABLE nextjs_posts (
  id SERIAL PRIMARY KEY,
  title VARCHAR(200) NOT NULL,
  slug VARCHAR(200) UNIQUE NOT NULL,
  content TEXT,
  excerpt TEXT,
  featured_image TEXT,
  metadata JSONB DEFAULT '{}',
  published BOOLEAN DEFAULT false,
  author_id INTEGER REFERENCES nextjs_users(id),
  view_count INTEGER DEFAULT 0,
  like_count INTEGER DEFAULT 0,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Comments table for user interactions
CREATE TABLE nextjs_comments (
  id SERIAL PRIMARY KEY,
  post_id INTEGER REFERENCES nextjs_posts(id) ON DELETE CASCADE,
  author_id INTEGER REFERENCES nextjs_users(id),
  content TEXT NOT NULL,
  parent_id INTEGER REFERENCES nextjs_comments(id),
  is_approved BOOLEAN DEFAULT false,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Sessions table for authentication
CREATE TABLE nextjs_sessions (
  id VARCHAR(255) PRIMARY KEY,
  user_id INTEGER REFERENCES nextjs_users(id) ON DELETE CASCADE,
  session_data JSONB NOT NULL,
  expires_at TIMESTAMP NOT NULL,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### Advanced Tables

```sql
-- Products table for e-commerce features
CREATE TABLE nextjs_products (
  id SERIAL PRIMARY KEY,
  name VARCHAR(200) NOT NULL,
  slug VARCHAR(200) UNIQUE NOT NULL,
  description TEXT,
  price DECIMAL(10,2) NOT NULL,
  category_id INTEGER,
  inventory_count INTEGER DEFAULT 0,
  metadata JSONB DEFAULT '{}',
  search_vector tsvector,
  is_active BOOLEAN DEFAULT true,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Analytics table for tracking
CREATE TABLE nextjs_analytics (
  id SERIAL PRIMARY KEY,
  event_type VARCHAR(50) NOT NULL,
  event_data JSONB NOT NULL,
  user_id INTEGER,
  session_id VARCHAR(255),
  ip_address INET,
  user_agent TEXT,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Cache table for ISR and optimization
CREATE TABLE nextjs_cache (
  key VARCHAR(255) PRIMARY KEY,
  value JSONB NOT NULL,
  expires_at TIMESTAMP NOT NULL,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

## 📈 Performance Considerations

### Connection Pooling

```javascript
// Optimal pool configuration for Next.js
const pool = new Pool({
  host: 'localhost',
  port: 5432,
  database: 'neondb',
  user: 'neon',
  password: 'npg',
  max: 20,                    // Maximum pool size
  idleTimeoutMillis: 30000,   // Close idle connections after 30s
  connectionTimeoutMillis: 10000, // Timeout after 10s
});
```

### Query Optimization

```javascript
// Use indexes for common queries
CREATE INDEX idx_posts_published ON nextjs_posts(published, created_at);
CREATE INDEX idx_users_email ON nextjs_users(email);
CREATE INDEX idx_sessions_expires ON nextjs_sessions(expires_at);

// Efficient pagination
const posts = await sql`
  SELECT id, title, excerpt, created_at
  FROM nextjs_posts
  WHERE published = true
  ORDER BY created_at DESC
  LIMIT 20 OFFSET ${page * 20}
`;
```

### Caching Strategies

```javascript
// ISR cache management
const cacheKey = `page:${pathname}`;
const cached = await sql`
  SELECT value FROM nextjs_cache
  WHERE key = ${cacheKey} AND expires_at > NOW()
`;

if (cached.length > 0) {
  return cached[0].value;
}

// Generate new content and cache
const content = await generatePageContent();
await sql`
  INSERT INTO nextjs_cache (key, value, expires_at)
  VALUES (${cacheKey}, ${JSON.stringify(content)}, ${new Date(Date.now() + 3600000)})
  ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value, expires_at = EXCLUDED.expires_at
`;
```

## 🛠️ Troubleshooting

### Common Issues

1. **Connection Timeout**
   ```
   Error: Connection timeout
   Solution: Check if Neon Local Proxy is running on localhost:5432
   ```

2. **Database Not Found**
   ```
   Error: database "neondb" does not exist
   Solution: Ensure both neondb and neondb_session databases are created
   ```

3. **Permission Denied**
   ```
   Error: permission denied for table
   Solution: Check database user permissions and table ownership
   ```

4. **WebSocket Connection Failed**
   ```
   Error: WebSocket connection failed
   Solution: Verify Neon serverless driver configuration and proxy settings
   ```

### Debug Mode

Enable debug logging by setting environment variables:

```bash
export DEBUG=neon:*
export PGDEBUG=1
node run-nextjs-tests.js
```

## 📚 Additional Resources

- [Next.js Documentation](https://nextjs.org/docs)
- [Neon Database Documentation](https://neon.tech/docs)
- [PostgreSQL Documentation](https://www.postgresql.org/docs/)
- [Node.js pg Library](https://node-postgres.com/)
- [Neon Serverless Driver](https://github.com/neondatabase/serverless)

## 🤝 Contributing

To add new tests or improve existing ones:

1. Follow the existing test structure and naming conventions
2. Add comprehensive error handling and cleanup
3. Include performance measurements where relevant
4. Update this README with new test descriptions
5. Ensure all tests pass before submitting changes

## 📄 License

This test suite is part of the Neon Local Proxy project and follows the same licensing terms.
