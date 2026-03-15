# Supabase RPC Manager
Execute stored procedures, vector search, and real-time operations.

## What This Does
- PostgreSQL RPC calls
- pgvector similarity search
- Real-time subscriptions
- Batch operations
- Transaction management

## Quick Example
```python
result = supabase.rpc('get_trial_balance', {
    'agency': 'RIM',
    'period': '2025-10'
})
```

## Getting Started
"Execute month-end closing RPC"
"Vector search similar expenses"
