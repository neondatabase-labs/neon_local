#!/usr/bin/env node

// Test: Prisma ORM with Neon adapter through HTTP proxy endpoint
import { config } from 'dotenv'

// Load environment variables from parent directory FIRST
config({ path: '../.env' });

// Set NODE_ENV to development BEFORE importing Neon modules
process.env.NODE_ENV = 'development';

import { neonConfig } from '@neondatabase/serverless'
import ws from 'ws';

// Configure Neon for local development - HTTP only, no WebSockets
// Do this BEFORE importing PrismaClient or PrismaNeon
neonConfig.fetchEndpoint = 'http://localhost:5432/sql'
neonConfig.useSecureWebSocket = false
neonConfig.poolQueryViaFetch = true  // Force HTTP queries instead of WebSocket

// WebSocket constructor wrapper that forces connections to localhost:5432
class LocalWebSocketWrapper extends ws {
  constructor(address, protocols, options) {
    // Parse the original URL to extract just the path and query
    const originalUrl = new URL(address.toString());
    
    // Create new URL with localhost:5432 but preserve path and query
    const localUrl = new URL(originalUrl.pathname + originalUrl.search, 'ws://localhost:5432');
    
    console.log(`WebSocket redirected from ${address} to ${localUrl.toString()}`);
    
    super(localUrl.toString(), protocols, options);
  }
}

neonConfig.webSocketConstructor = LocalWebSocketWrapper;

// NOW import Prisma modules after Neon is configured
import { PrismaClient } from '@prisma/client'
import { PrismaNeon } from '@prisma/adapter-neon'
import { neon } from '@neondatabase/serverless'

const globalForPrisma = globalThis;

// Create Prisma client with Neon adapter
// The neonConfig settings above will be used by the adapter internally
const adapter = new PrismaNeon({ connectionString: process.env.DATABASE_URL })
export const prisma = 
  globalForPrisma.prisma ??
  new PrismaClient({ adapter })

if (process.env.NODE_ENV !== 'production') globalForPrisma.prisma = prisma 

async function testPrismaNeonHttp() {
  console.log('🧪 Test: Prisma + Neon HTTP (with Neon Adapter)');

  const maxRetries = 3;
  const retryDelay = 2000; // 2 seconds

  for (let attempt = 1; attempt <= maxRetries; attempt++) {
    try {
      console.log(`  📡 Attempt ${attempt}/${maxRetries}: Testing Prisma with Neon adapter via HTTP proxy...`);
      
      // Test the connection and insert a record
      const result = await prisma.testRecord.create({
        data: {
          driver: 'Prisma + Neon Adapter via HTTP Proxy',
          status: 'success',
          message: 'HTTP proxy connection with Neon adapter successful'
        }
      });
      
      console.log('✅ PASS - Prisma + Neon Adapter HTTP Test');
      console.log('  Result:', JSON.stringify(result, null, 2));
      
      // Clean up
      await prisma.$disconnect();
      process.exit(0);
      
    } catch (error) {
      console.log(`  ⚠️  Attempt ${attempt} failed: ${error.message}`);
      
      // Clean up on error
      try {
        await prisma.$disconnect();
      } catch (cleanupError) {
        // Ignore cleanup errors
      }
      
      if (attempt === maxRetries) {
        console.log('❌ FAIL - Prisma + Neon Adapter HTTP Test');
        console.log('  Final error:', error.message);
        console.log('  Error details:', error.code || 'No error code');
        process.exit(1);
      } else {
        console.log(`  ⏳ Retrying in ${retryDelay/1000}s...`);
        await new Promise(resolve => setTimeout(resolve, retryDelay));
      }
    }
  }
}

async function runTest() {
  await testPrismaNeonHttp();
}

runTest();