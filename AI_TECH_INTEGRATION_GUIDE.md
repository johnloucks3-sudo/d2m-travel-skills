# Thunderbird AI Technology Integration Guide

## Current Architecture Overview

**Core Components**:
- MCP Server: `core/mcp/travel_mcp_server.py` (136/293 tools)
- Model Dispatcher: `agents/thunderbird_model_dispatcher.py`
- Telegram Integration: Multiple bot services
- REST API: `api/thunderbird_api.py` (port 8766)

**Current Model Stack**:
- Claude MAX (primary via OAuth)
- OpenCode + DeepSeek V3.1 (secondary)
- Budget: $0/month target

## Integration Architecture

### Proposed Multi-Model Router

```python
# core/ai_infra/model_router.py
class MultiModelRouter:
    def __init__(self):
        self.providers = {
            'claude_max': ClaudeProvider(),
            'mistral_next': MistralProvider(),
            'redpajama': RedPajamaProvider(),
            'cohere': CohereProvider()
        }
        self.cost_tracker = CostTracker()
        self.performance_monitor = PerformanceMonitor()
    
    async def route_task(self, task: Task, budget: float = None):
        """Intelligent task routing based on cost, performance, requirements"""
        candidate_models = self._select_candidates(task)
        best_model = self._optimize_selection(candidate_models, budget)
        return await self._execute_with_fallback(best_model, task)
```

### Provider Implementation Template

```python
# core/ai_infra/providers/mistral_provider.py
class MistralProvider:
    def __init__(self):
        self.client = MistralClient(api_key=os.getenv('MISTRAL_API_KEY'))
        self.cost_per_token = 0.0000012  # $1.2/M tokens
        
    async def execute(self, prompt: str, **kwargs):
        try:
            response = await self.client.chat.complete(
                model="mistral-next",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=kwargs.get('max_tokens', 4000)
            )
            cost = self._calculate_cost(response.usage)
            self.cost_tracker.record_usage('mistral', cost)
            return response.choices[0].message.content
        except Exception as e:
            raise ProviderError(f"Mistral API error: {e}")
```

## Integration Steps

### Step 1: Environment Setup

**Add to .env**:
```bash
# New AI Providers
MISTRAL_API_KEY=your_mistral_key
COHERE_API_KEY=your_cohere_key
TOGETHER_API_KEY=your_together_key
ALEPH_ALPHA_API_KEY=your_aleph_key

# Cost Tracking
AI_COST_BUDGET=50.0  # Monthly budget in USD
AI_COST_ALERT_THRESHOLD=40.0  # Alert at $40
```

### Step 2: Dependency Management

**Add to requirements.txt**:
```
# AI Provider SDKs
mistral-sdk>=0.3.0
cohere>=4.0.0
together>=0.2.0
aleph-alpha-client>=2.0.0

# Monitoring
prometheus-client>=0.20.0
grafana-dashboard>=1.0.0
```

### Step 3: Core Integration Files

**Create `core/ai_infra/__init__.py`**:
```python
"""AI Infrastructure module for multi-model management"""

from .model_router import MultiModelRouter
from .cost_tracker import CostTracker
from .performance_monitor import PerformanceMonitor
from .providers import *

# Global router instance
model_router = MultiModelRouter()
```

**Create `core/ai_infra/cost_tracker.py`**:
```python
class CostTracker:
    def __init__(self):
        self.monthly_budget = float(os.getenv('AI_COST_BUDGET', 50.0))
        self.current_month_cost = 0.0
        self.usage_history = []
    
    def record_usage(self, provider: str, cost: float):
        self.current_month_cost += cost
        self.usage_history.append({
            'timestamp': datetime.now(),
            'provider': provider,
            'cost': cost,
            'total_month': self.current_month_cost
        })
        
        if self.current_month_cost >= self.monthly_budget * 0.8:
            self._send_budget_alert()
```

### Step 4: Model Dispatcher Upgrade

**Update `agents/thunderbird_model_dispatcher.py`**:
```python
async def dispatch_task(task: str, model_preference: str = None):
    """Enhanced dispatcher with multi-model support"""
    
    # Route through multi-model router instead of direct Claude
    if should_use_cost_effective(task):
        result = await model_router.route_task(task, budget=0.1)
    elif requires_large_context(task):
        result = await model_router.route_task(task, provider_preference='mistral_next')
    elif requires_tool_use(task):
        result = await model_router.route_task(task, provider_preference='cohere')
    else:
        # Default to Claude for judgment/strategy
        result = await model_router.route_task(task, provider_preference='claude_max')
    
    return result
```

### Step 5: Telegram Bot Integration

**Update Telegram bot handlers**:
```python
# In message handlers, use intelligent routing
async def handle_client_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message.text
    
    # Use cost-effective model for simple queries
    if is_simple_query(message):
        response = await model_router.route_task(message, budget=0.05)
    else:
        # Use Claude for complex client interactions
        response = await model_router.route_task(message, provider_preference='claude_max')
    
    await update.message.reply_text(response)
```

### Step 6: Monitoring Dashboard

**Create `ops/ai_monitoring.py`**:
```python
"""AI cost and performance monitoring service"""

async def monitor_ai_usage():
    while True:
        current_cost = model_router.cost_tracker.current_month_cost
        budget = model_router.cost_tracker.monthly_budget
        
        if current_cost >= budget:
            await send_telegram_alert(f"⚠️ AI budget exceeded: ${current_cost:.2f}/${budget:.2f}")
        
        # Log performance metrics
        performance = model_router.performance_monitor.get_metrics()
        log_performance(performance)
        
        await asyncio.sleep(300)  # Check every 5 minutes
```

## Task Routing Logic

### Cost-Based Routing
```python
def should_use_cost_effective(task: str) -> bool:
    """Determine if task can use cheaper model"""
    simple_patterns = [
        r'(email|parse|extract)',
        r'(data|process|bulk)',
        r'(simple|quick|basic)'
    ]
    return any(re.search(pattern, task.lower()) for pattern in simple_patterns)
```

### Capability-Based Routing
```python
def requires_large_context(task: str) -> bool:
    """Check if task needs large context window"""
    context_patterns = [
        r'(itinerary|plan|document|full)',
        r'(analyze|review|comprehensive)',
        r'(multiple|complex|detailed)'
    ]
    return any(re.search(pattern, task.lower()) for pattern in context_patterns)
```

### Tool-Use Routing
```python
def requires_tool_use(task: str) -> bool:
    """Check if task involves API calls or tool use"""
    tool_patterns = [
        r'(api|integrate|call|connect)',
        r'(book|reserve|schedule)',
        r'(hotel|flight|transfer|car)',
        r'(price|availability|check)'
    ]
    return any(re.search(pattern, task.lower()) for pattern in tool_patterns)
```

## Fallback Strategy

```python
async def execute_with_fallback(provider_name: str, task: str, max_retries: int = 2):
    """Execute with automatic fallback to alternative providers"""
    providers = [provider_name] + FALLBACK_ORDER.get(provider_name, ['claude_max'])
    
    for attempt, current_provider in enumerate(providers):
        try:
            provider = model_router.providers[current_provider]
            result = await provider.execute(task)
            return result
        except Exception as e:
            if attempt >= max_retries:
                raise
            logger.warning(f"Provider {current_provider} failed, trying fallback: {e}")
```

## Cost Optimization Features

### Usage Quotas
```python
class UsageQuota:
    def __init__(self):
        self.quotas = {
            'redpajama': 1000000,  # 1M tokens/day
            'mistral_next': 200000,  # 200K tokens/day
            'cohere': 500000,       # 500K tokens/day
            'claude_max': 100000     # 100K tokens/day
        }
        self.daily_usage = {provider: 0 for provider in self.quotas}
    
    def can_use_provider(self, provider: str, estimated_tokens: int) -> bool:
        return (self.daily_usage[provider] + estimated_tokens) <= self.quotas[provider]
```

### Smart Caching
```python
class ResponseCache:
    def __init__(self, max_size: int = 1000):
        self.cache = {}
        self.max_size = max_size
    
    def get_cached_response(self, prompt: str) -> Optional[str]:
        prompt_hash = hashlib.md5(prompt.encode()).hexdigest()
        return self.cache.get(prompt_hash)
    
    def cache_response(self, prompt: str, response: str):
        if len(self.cache) >= self.max_size:
            # Remove oldest entry
            oldest_key = next(iter(self.cache))
            del self.cache[oldest_key]
        
        prompt_hash = hashlib.md5(prompt.encode()).hexdigest()
        self.cache[prompt_hash] = response
```

## Deployment Strategy

### Phase 1: Shadow Mode
- Run new models in parallel but don't use responses
- Compare cost and performance metrics
- Build confidence in routing logic

### Phase 2: Canary Deployment
- Route 10% of traffic to new system
- Monitor for errors and cost savings
- Gradually increase percentage

### Phase 3: Full Deployment
- 100% traffic through multi-model router
- Continuous optimization based on metrics
- Regular review of cost-performance tradeoffs

## Monitoring & Alerting

### Key Metrics to Track:
1. **Cost per task**: Average cost across providers
2. **Response time**: Performance comparison
3. **Error rates**: Provider reliability
4. **Token usage**: Efficiency metrics
5. **Cache hit rate**: Optimization effectiveness

### Alert Thresholds:
- Cost > 80% of monthly budget
- Error rate > 5% for any provider
- Response time > 30s for critical tasks
- Cache hit rate < 20% (indicates need for optimization)

## Rollback Plan

### Emergency Switch:
```python
def emergency_fallback():
    """Revert to original Claude-only mode"""
    global model_router
    model_router = LegacyClaudeRouter()  # Simple wrapper around Claude
    logger.critical("Emergency fallback activated - using Claude-only mode")
```

This integration guide provides a comprehensive framework for enhancing Thunderbird's AI capabilities while maintaining cost control and reliability.