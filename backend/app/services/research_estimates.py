"""Versioned workload ranges, independent of parallelism and provider pricing."""
import math

VERSION = 'workload-v1'


def workload_label(upper):
    return 'low' if upper < 100_000 else 'medium' if upper < 500_000 else 'high' if upper < 2_000_000 else 'extra_high'


def source_tokens(text):
    # Unicode-aware approximation for extracted text, never uploaded file bytes.
    wide = sum(ord(c) > 0x2fff for c in text)
    return max(1, math.ceil((len(text)-wide)/4 + wide))


def request_observations(records, settings):
    """Keep broad bounds, informed by earlier requests on this model path."""
    sizes = sorted(r['input_tokens'] + r['output_tokens'] for r in records
        if r.get('provider') == settings['provider'] and r.get('model') == settings['model']
        and r.get('input_tokens') is not None and r.get('output_tokens') is not None
        and not r.get('error'))
    if len(sizes) < 3:
        return {}
    return {'request_token_range': [max(4000, math.floor(sizes[len(sizes)//4] * .5)),
                                    max(32000, math.ceil(sizes[min(len(sizes)-1, math.floor(len(sizes)*.9))] * 2))]}


def estimate(text, settings, plan=None, observations=None):
    tokens = source_tokens(text)
    plan, observations = plan or {}, observations or {}
    agents = [plan['agents']]*2 if plan.get('agents') else [max(3,min(12,math.ceil(tokens/1800))), max(8,min(60,math.ceil(tokens/350)+5))]
    rounds = [plan['rounds']]*2 if plan.get('rounds') else [24,336]
    fraction = {'quick':.25,'moderate':.5,'full':1}[settings['depth']]
    rounds = [max(1,math.ceil(r*fraction)) for r in rounds]
    platforms = 2 if settings['platform'] == 'parallel' else 1
    activation = observations.get('activation_rate_range', [.15,.6])
    request_size = observations.get('request_token_range', [4000,32000])
    stages = {
        'analysis_graph':[tokens*3+4000, tokens*30+24000],
        'preparation':[agents[0]*2500+6000, agents[1]*9000+24000],
        'simulation_memory':[math.ceil(agents[0]*rounds[0]*platforms*activation[0]*request_size[0]*1.1),
                             math.ceil(agents[1]*rounds[1]*platforms*activation[1]*request_size[1]*1.5)],
        'report':[20000,150000],
    }
    lower, upper = [sum(v[i] for v in stages.values()) for i in (0,1)]
    return {'version':VERSION,'lower':lower,'upper':upper,'label':workload_label(upper),
        'confidence':'refined' if plan else 'preliminary', 'reasoning_coverage':'unknown',
        'stages':stages, 'assumptions':{'source_tokens':tokens,'agents':agents,'rounds':rounds,
        'platforms':platforms,'activation_rate':activation,'tokens_per_request':request_size,
        'includes':['source_analysis','graph_extraction','personas','repeated_history','memory','report'],
        'excludes':['unreported_reasoning_tokens'], 'measured_request_sizes':bool(observations.get('request_token_range'))},
        'thresholds':{'low':100000,'medium':500000,'high':2000000}}
