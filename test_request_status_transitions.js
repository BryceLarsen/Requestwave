#!/usr/bin/env node
/**
 * Request Status Transition Test Script
 * 
 * Tests all status transitions for request management:
 * - pending -> up_next, played, rejected
 * - up_next -> played, rejected
 * - archive transitions
 * 
 * Usage: node test_request_status_transitions.js [api_url] [email] [password]
 */

const axios = require('axios');

// Configuration
const API_URL = process.argv[2] || 'https://requestwave.app/api';
const TEST_EMAIL = process.argv[3] || 'brycelarsenmusic@gmail.com';
const TEST_PASSWORD = process.argv[4] || 'RequestWave2024!';

let token = null;
let musicianId = null;
let testRequests = [];

// Colored console output
const colors = {
  reset: '\x1b[0m',
  red: '\x1b[31m',
  green: '\x1b[32m',
  yellow: '\x1b[33m',
  blue: '\x1b[34m'
};

function log(color, message) {
  console.log(`${color}${message}${colors.reset}`);
}

function logPass(test) {
  log(colors.green, `✓ PASS: ${test}`);
}

function logFail(test, error) {
  log(colors.red, `✗ FAIL: ${test}`);
  if (error) log(colors.red, `  Error: ${error}`);
}

function logInfo(message) {
  log(colors.blue, `ℹ ${message}`);
}

// Test Functions
async function authenticate() {
  try {
    const response = await axios.post(`${API_URL}/auth/login`, {
      email: TEST_EMAIL,
      password: TEST_PASSWORD
    });
    
    token = response.data.token;
    musicianId = response.data.musician.id;
    logPass(`Authenticated as ${response.data.musician.name}`);
    return true;
  } catch (error) {
    logFail('Authentication', error.response?.data?.detail || error.message);
    return false;
  }
}

async function getSongs() {
  try {
    const response = await axios.get(`${API_URL}/songs`, {
      headers: { 'Authorization': `Bearer ${token}` }
    });
    
    if (response.data.length > 0) {
      logPass(`Retrieved ${response.data.length} songs`);
      return response.data.slice(0, 5); // Return first 5 songs
    } else {
      logFail('Get Songs', 'No songs found');
      return [];
    }
  } catch (error) {
    logFail('Get Songs', error.response?.data?.detail || error.message);
    return [];
  }
}

async function createTestRequest(song, requesterName) {
  try {
    const response = await axios.post(`${API_URL}/requests`, {
      song_id: song.id,
      requester_name: requesterName,
      requester_email: 'test@example.com',
      dedication: `Test request for ${song.title}`
    });
    
    const requestId = response.data.id;
    testRequests.push(requestId);
    return requestId;
  } catch (error) {
    logFail('Create Test Request', error.response?.data?.detail || error.message);
    return null;
  }
}

async function updateStatus(requestId, status) {
  try {
    const response = await axios.put(
      `${API_URL}/requests/${requestId}/status`,
      { status },
      { headers: { 'Authorization': `Bearer ${token}` } }
    );
    return response.data.success;
  } catch (error) {
    throw new Error(error.response?.data?.detail || error.message);
  }
}

async function archiveRequest(requestId) {
  try {
    const response = await axios.put(
      `${API_URL}/requests/${requestId}/archive`,
      {},
      { headers: { 'Authorization': `Bearer ${token}` } }
    );
    return response.data.success;
  } catch (error) {
    throw new Error(error.response?.data?.detail || error.message);
  }
}

async function cleanupRequests() {
  logInfo('Cleaning up test requests...');
  let cleaned = 0;
  for (const requestId of testRequests) {
    try {
      await axios.delete(`${API_URL}/requests/${requestId}`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      cleaned++;
    } catch (error) {
      // Ignore cleanup errors
    }
  }
  logInfo(`Cleaned up ${cleaned}/${testRequests.length} test requests`);
}

// Main test suite
async function runTests() {
  console.log('\n=== Request Status Transition Tests ===\n');
  
  // Authenticate
  if (!await authenticate()) {
    process.exit(1);
  }
  
  // Get songs
  const songs = await getSongs();
  if (songs.length === 0) {
    console.log('\nCannot run tests without songs. Please add songs first.');
    process.exit(1);
  }
  
  console.log('\n--- Status Update Tests ---\n');
  
  // Test 1: pending -> played
  try {
    const requestId = await createTestRequest(songs[0], 'Test User 1');
    if (requestId) {
      await updateStatus(requestId, 'played');
      logPass('pending -> played transition');
    }
  } catch (error) {
    logFail('pending -> played transition', error.message);
  }
  
  // Test 2: pending -> rejected
  try {
    const requestId = await createTestRequest(songs[1], 'Test User 2');
    if (requestId) {
      await updateStatus(requestId, 'rejected');
      logPass('pending -> rejected transition');
    }
  } catch (error) {
    logFail('pending -> rejected transition', error.message);
  }
  
  // Test 3: pending -> up_next
  try {
    const requestId = await createTestRequest(songs[2], 'Test User 3');
    if (requestId) {
      await updateStatus(requestId, 'up_next');
      logPass('pending -> up_next transition');
    }
  } catch (error) {
    logFail('pending -> up_next transition', error.message);
  }
  
  // Test 4: up_next -> played
  try {
    const requestId = await createTestRequest(songs[3], 'Test User 4');
    if (requestId) {
      await updateStatus(requestId, 'up_next');
      await updateStatus(requestId, 'played');
      logPass('up_next -> played transition');
    }
  } catch (error) {
    logFail('up_next -> played transition', error.message);
  }
  
  // Test 5: pending -> accepted
  try {
    const requestId = await createTestRequest(songs[4], 'Test User 5');
    if (requestId) {
      await updateStatus(requestId, 'accepted');
      logPass('pending -> accepted transition');
    }
  } catch (error) {
    logFail('pending -> accepted transition', error.message);
  }
  
  console.log('\n--- Archive Tests ---\n');
  
  // Test 6: Archive request
  try {
    const requestId = await createTestRequest(songs[0], 'Archive Test');
    if (requestId) {
      await archiveRequest(requestId);
      logPass('Archive request');
    }
  } catch (error) {
    logFail('Archive request', error.message);
  }
  
  // Test 7: Reject archived status via status endpoint
  try {
    const requestId = await createTestRequest(songs[1], 'Invalid Status Test');
    if (requestId) {
      try {
        await updateStatus(requestId, 'archived');
        logFail('Should reject archived status', 'Status endpoint accepted archived status');
      } catch (error) {
        if (error.message.includes('Invalid status') || error.message.includes('400')) {
          logPass('Correctly rejects archived status via status endpoint');
        } else {
          logFail('Should reject archived status', error.message);
        }
      }
    }
  } catch (error) {
    logFail('Invalid status test', error.message);
  }
  
  // Cleanup
  console.log('');
  await cleanupRequests();
  
  console.log('\n=== Tests Complete ===\n');
}

// Run tests
runTests().catch(error => {
  console.error('Test runner error:', error);
  process.exit(1);
});
