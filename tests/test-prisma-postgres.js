#!/usr/bin/env node

// Test: Prisma ORM with PostgreSQL driver
import { PrismaClient } from '@prisma/client';

async function testPrismaPostgreSQL() {
  console.log('🧪 Test: Prisma + PostgreSQL');

  const maxRetries = 3;
  const retryDelay = 2000; // 2 seconds

  for (let attempt = 1; attempt <= maxRetries; attempt++) {
    let prisma = null;
    
    try {
      console.log(`  📡 Attempt ${attempt}/${maxRetries}: Testing Prisma + PostgreSQL...`);
      
      // Initialize Prisma client with direct PostgreSQL connection
      // This will use the standard PostgreSQL protocol through the proxy
      prisma = new PrismaClient({
        datasources: {
          db: {
            url: 'postgresql://neon:npg@localhost:5432/neondb?sslmode=require'
          }
        },
        log: ['error'] // Only log errors to reduce noise
      });
      
      // Ensure the test_records table exists
      await prisma.$executeRaw`
        CREATE TABLE IF NOT EXISTS test_records (
          id SERIAL PRIMARY KEY,
          driver VARCHAR(255),
          timestamp TIMESTAMP DEFAULT NOW(),
          status VARCHAR(50),
          message TEXT
        )
      `;
      
      // Test the connection and insert a record
      const result = await prisma.testRecord.create({
        data: {
          driver: 'Prisma + PostgreSQL',
          status: 'success', 
          message: 'Direct PostgreSQL connection test successful'
        }
      });
      
      console.log('✅ PASS - Prisma + PostgreSQL Test');
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
        console.log('❌ FAIL - Prisma + PostgreSQL Test');
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

testPrismaPostgreSQL();
