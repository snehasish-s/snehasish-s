#!/usr/bin/env python3
"""Generate warm, self-hosted GitHub profile SVG cards using public GitHub API data.
Requires only Python stdlib. Designed to run in GitHub Actions, not on visitor page loads.
"""
import json
import os
import urllib.request
from collections import defaultdict
from pathlib import Path
from xml.sax.saxutils import escape

USER = os.getenv('GITHUB_USER', 'snehasish-s')
TOKEN = os.getenv('GITHUB_TOKEN', '')
BASE = 'https://api.github.com'
OUT = Path('assets')
OUT.mkdir(parents=True, exist_ok=True)

def fetch(path):
    headers = {
        'Accept': 'application/vnd.github+json',
        'User-Agent': f'{USER}-profile-metrics',
        'X-GitHub-Api-Version': '2022-11-28',
    }
    if TOKEN:
        headers['Authorization'] = 'Bearer ' + TOKEN
    req = urllib.request.Request(BASE + path, headers=headers)
    with urllib.request.urlopen(req, timeout=25) as response:
        return json.load(response)

def shell(title, subtitle, inner, bg='#FAF1E8'):
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="600" height="240" viewBox="0 0 600 240" role="img" aria-label="{escape(title)}">
<style>.glow{{animation:p 2.8s ease-in-out infinite}}@keyframes p{{50%{{opacity:.25}}}}@media(prefers-reduced-motion:reduce){{*{{animation:none!important}}}}</style>
<rect width="599" height="239" x=".5" y=".5" rx="20" fill="{bg}" stroke="#DFC8C0"/>
<text x="32" y="48" font-family="Georgia,serif" font-size="27" font-weight="bold" fill="#47333B">{escape(title)}</text>
<text x="32" y="74" font-family="Arial,sans-serif" font-size="15" fill="#977477">{escape(subtitle)}</text>
<circle class="glow" cx="565" cy="35" r="7" fill="#C56E55"/>
{inner}</svg>"""

def text(x, y, value, size=18, color='#785E64', weight='normal', anchor='start'):
    return f'<text x="{x}" y="{y}" font-family="Arial,sans-serif" font-size="{size}" font-weight="{weight}" text-anchor="{anchor}" fill="{color}">{escape(str(value))}</text>'

def metrics(profile, repos):
    values = [
        (len(repos), 'Public repos'),
        (profile.get('followers',0), 'Followers'),
        (sum(r.get('stargazers_count',0) for r in repos), 'Repo stars'),
        (sum(r.get('forks_count',0) for r in repos), 'Repo forks')
    ]
    xvals = [83, 226, 374, 519]
    chunks = ['<path d="M28 112 H572" stroke="#DBC6BC"/>']
    for (value, caption),x in zip(values,xvals):
        chunks.append(text(x,156, f'{value:,}', 31,'#A65C50','bold','middle'))
        chunks.append(text(x,186,caption,16,'#745E60','normal','middle'))
    chunks.append(text(32, 219, 'Public GitHub data · refreshed by Actions', 13, '#988077'))
    return shell('GitHub at a glance',f'@{USER} · public repositories', ''.join(chunks))

def languages(items):
    colors=['#C36E57','#7B5E75','#BB8D50','#648474','#B58A8E']
    total = sum(v for _,v in items)
    bits=[text(32,101, 'Languages by public repository bytes', 15, '#906E79')]
    if not total:
        bits.append(text(32,156,'No public language data available',19))
    else:
        x=32
        for i,(lang,val) in enumerate(items[:5]):
            w=534*val/total
            bits.append(f'<rect x="{x:.1f}" y="116" width="{w:.1f}" height="23" rx="3" fill="{colors[i]}"/>')
            x+=w
        for i,(lang,val) in enumerate(items[:5]):
            col=i%3
            row=i//3
            px=32+col*183
            py=164+row*30
            pct=(100*val/total)
            bits.append(f'<circle cx="{px+7}" cy="{py-5}" r="6" fill="{colors[i]}"/>')
            bits.append(text(px+19, py, f'{lang} {pct:.0f}%', 14, '#62515A'))
    return shell('Languages in my repos', f'@{USER} · public code only', ''.join(bits), '#F3E9EB')

def main():
    profile=fetch('/users/'+USER)
    repos=[]
    for page in range(1,7):
        page_repos=fetch(f'/users/{USER}/repos?per_page=100&page={page}&type=owner&sort=updated')
        if not page_repos: break
        repos += [r for r in page_repos if not r.get('fork') and not r.get('private')]
        if len(page_repos)<100:break
    # Exclude forks, and sample up to 70 active repositories for language bytes to keep
    # the API load and workflow duration reasonable.
    counter=defaultdict(int)
    for r in repos[:70]:
        try:
            for lang,size in fetch('/repos/'+USER+'/'+r['name']+'/languages').items():
                counter[lang]+=size
        except Exception as e:
            print('Skipped language data for',r['name'],str(e))
    (OUT/'metrics.svg').write_text(metrics(profile,repos),encoding='utf-8')
    (OUT/'languages.svg').write_text(languages(sorted(counter.items(),key=lambda kv:kv[1],reverse=True)),encoding='utf-8')
    print('Generated metrics and languages SVG for',USER)

if __name__ == '__main__':
    main()
