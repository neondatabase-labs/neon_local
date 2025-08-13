#!/usr/bin/env node

// Test: Prisma ORM through HTTP proxy endpoint
import { PrismaClient } from '@prisma/client';

async function testPrismaNeonHttp() {
  console.log('🧪 Test: Prisma + Neon HTTP');

  const maxRetries = 3;
  const retryDelay = 2000; // 2 seconds

  for (let attempt = 1; attempt <= maxRetries; attempt++) {
    let prisma = null;
    
    try {
      console.log(`  📡 Attempt ${attempt}/${maxRetries}: Testing Prisma via HTTP proxy...`);
      
      // Initialize Prisma client to connect through the proxy using HTTP
      // This will use standard PostgreSQL protocol through the proxy
      prisma = new PrismaClient({
        datasources: {
          db: {
            url: 'postgresql://neon:npg@localhost:5432/neondb?sslmode=require'
          }
        },
        log: ['error'] // Only log errors to reduce noise
      });
      
      // Test the connection and insert a record
      const result = await prisma.testRecord.create({
        data: {
          driver: 'Prisma via HTTP Proxy',
          status: 'success',
          message: 'HTTP proxy connection successful'
        }
      });
      
      console.log('✅ PASS - Prisma via HTTP Proxy Test');
      console.log('  Result:', JSON.stringify(result, null, 2));
      
      // Clean up
      await prisma.$disconnect();
      process.exit(0);
      
    } catch (error) {
      console.log(`  ⚠️  Attempt ${attempt} failed: ${error.message}`);
      
      // Clean up on error
      if (prisma) {
        try {
          await prisma.$disconnect();
        } catch (cleanupError) {
          // Ignore cleanup errors
        }
      }
      
      if (attempt === maxRetries) {
        console.log('❌ FAIL - Prisma via HTTP Proxy Test');
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
