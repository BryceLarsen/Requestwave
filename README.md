# RequestWave - Free GA Branch

RequestWave is a live music request platform that enables musicians to manage song requests, interact with their audience, and receive tips during performances.

## Free GA Mode (Default)

This branch runs in **Free GA mode** by default, where all features are unlocked without any billing or payment processing.

### Feature Flag Configuration

The application uses a global `BILLING_ENABLED` feature flag to control billing functionality:

- **Default**: `BILLING_ENABLED=false` (Free GA mode)
- **Location**: Backend `.env` and frontend `.env` files

#### Backend Configuration (.env)
```
BILLING_ENABLED=false
```

#### Frontend Configuration (.env)
```
REACT_APP_BILLING_ENABLED=false
```

### Free vs Paid Mode Behavior

#### When BILLING_ENABLED=false (Free GA - Default):
- ✅ All features unlocked for all users
- ✅ No Stripe integration required
- ✅ Audience links always active
- ✅ Full dashboard access
- ✅ Unlimited song requests
- ✅ Complete playlist management
- ✅ Analytics and insights
- ❌ No subscription UI or billing flows

#### When BILLING_ENABLED=true (Paid Mode - Opt-in):
- 🔐 Freemium model with 14-day trial
- 💳 Stripe integration for subscriptions
- 📊 Audience link activation requires payment
- 💰 Subscription management UI visible

### Switching Between Modes

To enable billing functionality:

1. Update environment variables:
   ```bash
   # Backend
   echo "BILLING_ENABLED=true" >> backend/.env
   
   # Frontend  
   echo "REACT_APP_BILLING_ENABLED=true" >> frontend/.env
   ```

2. Configure Stripe settings in backend `.env`:
   ```
   STRIPE_API_KEY=sk_live_...
   STRIPE_WEBHOOK_SECRET=whsec_...
   PRICE_MONTHLY_5=price_...
   PRICE_ANNUAL_48=price_...
   ```

3. Restart the application

### API Behavior

#### Free Mode (BILLING_ENABLED=false):
- `GET /api/subscription/status` → Returns pro-like status with all features enabled
- `POST /api/subscription/checkout` → Returns 501 "Billing disabled in Free mode"
- `POST /api/subscription/cancel` → Returns 501 "Billing disabled in Free mode"
- `POST /api/stripe/webhook` → Returns 204 (no-op)

#### Paid Mode (BILLING_ENABLED=true):
- All subscription endpoints function normally with Stripe integration
- Freemium model with trial periods and payment processing

## Quick Start

1. Clone the repository
2. Install dependencies
3. Start in Free GA mode (no additional configuration needed)
4. All features are immediately available

The free version provides the complete RequestWave experience without any limitations or setup complexity.
