"""Build the offline HTML report from the final Markdown, using the standard library."""
import html
import json
import re
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
REPO='https://github.com/ElmerElla/simultaneous-translation-benchmark'
DOWNLOAD=REPO+'/releases/download/v1.0-20261106/'


def inline(text):
    text=html.escape(text)
    text=re.sub(r'`([^`]+)`',r'<code>\1</code>',text)
    text=re.sub(r'\*\*([^*]+)\*\*',r'<strong>\1</strong>',text)
    def link(m):
        label,url=m.groups();url=url.replace('../evidence/','evidence/')
        if url.startswith(DOWNLOAD):
            filename=url[len(DOWNLOAD):];bare=filename.split('#')[0];point=filename.split('#t=')[-1] if '#t=' in filename else '0'
            return f'<a class="seek" href="media/{filename}" data-video="{bare[:-4]}" data-time="{point}">{label}</a>'
        if url=='reproducibility.md':url='docs/reproducibility.md'
        if url=='privacy.md':url='docs/privacy.md'
        if url=='../测试结论.xlsx':url='测试结论.xlsx'
        return f'<a href="{url}">{label}</a>'
    return re.sub(r'\[([^\]]+)\]\(([^)]+)\)',link,text)


def render(markdown,products,media):
    lines=markdown.splitlines();parts=[];nav=[];i=0
    by_name={p['name']:p for p in products}
    while i<len(lines):
        line=lines[i]
        if not line.strip():i+=1;continue
        if line.startswith('#'):
            level=len(line)-len(line.lstrip('#'));text=line[level:].strip()
            ident=by_name[text]['slug'] if text in by_name else 'section-'+str(len(nav))+'-'+str(i)
            parts.append(f'<h{level} id="{ident}">{inline(text)}</h{level}>')
            if level==2:nav.append((ident,text))
            if text in by_name:
                p=by_name[text]
                parts.append('<div class="video-list">')
                for m in media:
                    if m['product']!=p['slug']:continue
                    case=next(c for c in p['cases'] if c['video_id']==m['id'])
                    parts.append(f'<figure class="video-card"><figcaption><strong>{m["id"]}</strong> <span>{m["public_duration_s"]:.1f} 秒 · 脱敏浏览副本</span></figcaption><video id="video-{m["id"]}" controls playsinline preload="none" poster="{case["evidence_image"]}" src="media/{m["file"]}"></video><a href="{DOWNLOAD}{m["file"]}">单独下载视频</a></figure>')
                parts.append('</div>')
            i+=1;continue
        if line.startswith('|'):
            rows=[]
            while i<len(lines) and lines[i].startswith('|'):
                cells=[c.strip() for c in lines[i].strip().strip('|').split('|')]
                if not all(re.fullmatch(r'[:\- ]+',c) for c in cells):rows.append(cells)
                i+=1
            parts.append('<div class="table-scroll"><table>')
            for j,row in enumerate(rows):
                tag='th' if j==0 else 'td'
                parts.append('<tr>'+''.join(f'<{tag}>{inline(c)}</{tag}>' for c in row)+'</tr>')
            parts.append('</table></div>');continue
        if line.startswith('- '):
            items=[]
            while i<len(lines) and lines[i].startswith('- '):items.append('<li>'+inline(lines[i][2:])+'</li>');i+=1
            parts.append('<ul>'+''.join(items)+'</ul>');continue
        im=re.fullmatch(r'!\[([^\]]*)\]\(([^)]+)\)',line)
        if im:
            label,url=im.groups();url=url.replace('../evidence/','evidence/')
            parts.append(f'<figure class="evidence"><a href="{html.escape(url)}"><img loading="lazy" alt="{html.escape(label)}" src="{html.escape(url)}"></a><figcaption>{html.escape(label)} · 点击查看原尺寸</figcaption></figure>');i+=1;continue
        paragraph=[line];i+=1
        while i<len(lines) and lines[i].strip() and not lines[i].startswith(('#','|','- ','![')):
            paragraph.append(lines[i]);i+=1
        parts.append('<p>'+inline('\n'.join(paragraph)).replace('\n','<br>')+'</p>')
    toc=''.join(f'<a href="#{ident}">{html.escape(text)}</a>' for ident,text in nav)
    css='''*{box-sizing:border-box}html{scroll-behavior:smooth}body{margin:0;color:#243447;background:#f4f6f8;font:16px/1.85 "Segoe UI","Microsoft YaHei",sans-serif}a{color:#176e97;text-decoration:none}a:hover{text-decoration:underline}aside{position:fixed;inset:0 auto 0 0;width:245px;padding:38px 24px;background:#172e42;color:#dce7ef;overflow-y:auto}aside b{display:block;font-size:22px;color:white;line-height:1.6;margin-bottom:8px}aside small{color:#a8becd}nav{margin-top:30px}nav a{display:block;color:#dce7ef;padding:7px 0;font-size:14px}main{max-width:1310px;margin-left:245px;padding:48px 54px 100px}article{background:white;border:1px solid #e0e7ed;border-radius:14px;padding:38px 46px;box-shadow:0 6px 24px #172e4206}h1{font-size:36px;line-height:1.45;margin:0 0 20px;color:#15364c}h2{scroll-margin-top:24px;border-top:1px solid #e0e7ed;padding-top:38px;margin-top:46px;font-size:26px;color:#183e55}h3{font-size:19px;margin:28px 0 10px;color:#245d78}p{margin:12px 0 20px}li{margin:10px 0}.table-scroll{overflow-x:auto;margin:24px 0 30px}table{border-collapse:collapse;width:100%;font-size:14px;line-height:1.7}th{background:#e9f0f4;color:#234b63;text-align:left;white-space:nowrap}td,th{padding:12px 14px;border:1px solid #dbe4eb;vertical-align:top}tbody tr:nth-child(even),tr:nth-child(even){background:#f8fafb}code{font-size:.9em;border-radius:4px;background:#edf2f5;padding:2px 5px;overflow-wrap:anywhere}.video-list{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:18px;margin:26px 0}.video-card{border:1px solid #dce5eb;background:#f7fafc;border-radius:8px;margin:0;padding:14px}.video-card figcaption{font-size:13px;margin-bottom:10px;display:flex;flex-wrap:wrap;gap:6px}.video-card span{color:#69808e}video{width:100%;aspect-ratio:16/9;background:#000;border-radius:4px}.video-card>a{font-size:13px}.evidence{margin:20px 0 38px;border:1px solid #dfe6ec;background:#f8fafb;border-radius:8px;padding:16px}.evidence img{display:block;max-width:100%;max-height:650px;width:auto;margin:auto}.evidence figcaption{font-size:12px;color:#6f8290;margin-top:10px;text-align:center}.notice{border-left:3px solid #2194ae;background:#edf7fa;padding:12px 18px;margin:0 0 30px;font-size:14px}.top{font-size:12px;letter-spacing:2px;color:#7b91a0;margin-bottom:12px}.summary{display:flex;gap:12px;margin:22px 0}.summary span{padding:9px 15px;background:#f0f6f8;border:1px solid #d7e5eb;border-radius:7px;font-size:14px}@media(max-width:1000px){aside{display:none}main{margin-left:0;padding:24px 16px}article{padding:24px}.video-list{grid-template-columns:1fr}h1{font-size:28px}}@media print{aside,.video-list{display:none}main{margin:0;padding:0}article{border:0;box-shadow:none;padding:10px}a{color:inherit}.evidence{break-inside:avoid}h2{break-before:page}}'''
    js='''document.querySelectorAll('a.seek').forEach(a=>a.addEventListener('click',e=>{const v=document.getElementById('video-'+a.dataset.video);if(!v)return;e.preventDefault();v.scrollIntoView({behavior:'smooth',block:'center'});const seek=()=>{v.currentTime=Number(a.dataset.time);v.pause();};if(v.readyState>=1)seek();else{v.addEventListener('loadedmetadata',seek,{once:true});v.load();}}));'''
    return '<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="referrer" content="no-referrer"><title>七款同声传译软件测试报告</title><style>'+css+'</style></head><body><aside><b>同声传译<br>测试报告</b><small>Windows · 中译英<br>2026 年 11 月</small><nav>'+toc+'</nav></aside><main><div class="top">SIMULTANEOUS TRANSLATION · EVIDENCE REVIEW</div><article><div class="notice">本地离线文档。测试朗读与克隆声音获准保留，个人界面区域已遮挡。视频需随完整包解压至 media/；定量结论来自本地原件。</div><div class="summary"><span>7 款软件</span><span>47 组证据</span><span>19 段视频</span></div>'+''.join(parts)+'<h2>测试输入音频</h2><p>S01 统一语料：</p><audio controls preload="none" src="media/s01-input.wav"></audio><p>Transync 声音克隆参考样本：</p><audio controls preload="none" src="media/clone-reference.wav"></audio></article></main><script>'+js+'</script></body></html>'


def main():
    markdown=(ROOT/'docs/report.md').read_text(encoding='utf-8')
    products=json.loads((ROOT/'data/results.json').read_text(encoding='utf-8'))
    media=json.loads((ROOT/'data/media-manifest.json').read_text(encoding='utf-8'))
    (ROOT/'report.html').write_text(render(markdown,products,media),encoding='utf-8')
    print('Built report.html from final Markdown')


if __name__=='__main__':main()
