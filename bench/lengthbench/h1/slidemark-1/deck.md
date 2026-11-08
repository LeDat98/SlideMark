theme: none
lang: en
colors: bg=#FFFFFF fg=#1E2A32 primary=#1F3A34 secondary=#4F8A7B accent=#E4572E surface=#EEF3F1 border=#C9D6D1 muted=#5E6B66
fonts: heading="Georgia" body="Calibri"
sizes: title=38! heading=20 body=16 lead=20 conclusion=20
style: title.band=none border=border radius=6
footer: Support review, Q3
num: on

# Support review, Q3 {align=left}
## Why tickets rose and what we change

# Why ticket volume rose 40%
@noemph defaults
```html
<div style="position:relative;width:1180px;height:400px;font-size:18px">
<svg viewBox="0 0 1180 400" style="position:absolute;left:0;top:0;width:1180px;height:400px">
<line x1="30" y1="200" x2="900" y2="200" stroke="#1F3A34" stroke-width="4"/>
<line x1="120" y1="112" x2="190" y2="200" stroke="#4F8A7B" stroke-width="3"/>
<line x1="550" y1="112" x2="620" y2="200" stroke="#4F8A7B" stroke-width="3"/>
<line x1="190" y1="200" x2="120" y2="288" stroke="#E4572E" stroke-width="3"/>
<line x1="620" y1="200" x2="550" y2="288" stroke="#4F8A7B" stroke-width="3"/>
</svg>
<div style="position:absolute;left:30px;top:0;width:340px;height:36px;background:#4F8A7B;color:#fff;font-weight:bold;display:flex;align-items:center;justify-content:center">People</div>
<div style="position:absolute;left:30px;top:44px;width:340px;height:64px;border:1px solid #C9D6D1;background:#EEF3F1;padding:8px">new hires in July; no weekend cover</div>
<div style="position:absolute;left:460px;top:0;width:340px;height:36px;background:#4F8A7B;color:#fff;font-weight:bold;display:flex;align-items:center;justify-content:center">Process</div>
<div style="position:absolute;left:460px;top:44px;width:340px;height:64px;border:1px solid #C9D6D1;background:#EEF3F1;padding:8px">refunds need two approvals</div>
<div style="position:absolute;left:30px;top:294px;width:340px;height:64px;border:2px solid #E4572E;background:#FDECE6;padding:8px">app update 4.2 broke login</div>
<div style="position:absolute;left:30px;top:360px;width:340px;height:36px;background:#E4572E;color:#fff;font-weight:bold;display:flex;align-items:center;justify-content:center">Product</div>
<div style="position:absolute;left:460px;top:294px;width:340px;height:64px;border:1px solid #C9D6D1;background:#EEF3F1;padding:8px">courier API outage in August</div>
<div style="position:absolute;left:460px;top:360px;width:340px;height:36px;background:#4F8A7B;color:#fff;font-weight:bold;display:flex;align-items:center;justify-content:center">Partners</div>
<div style="position:absolute;left:910px;top:140px;width:270px;height:120px;background:#1F3A34;color:#fff;font-weight:bold;font-size:32px;display:flex;align-items:center;justify-content:center">Tickets +40%</div>
</div>
```
> The main cause is the app update 4.2 login bug.

# Fix plan, status this week
@noemph defaults
```html
<div style="position:relative;width:1180px;height:490px;font-size:20px">
<div style="position:absolute;left:0;top:0;width:370px;height:490px;background:#EEF3F1;border:1px solid #C9D6D1"></div>
<div style="position:absolute;left:405px;top:0;width:370px;height:490px;background:#EEF3F1;border:1px solid #C9D6D1"></div>
<div style="position:absolute;left:810px;top:0;width:370px;height:490px;background:#EEF3F1;border:1px solid #C9D6D1"></div>
<div style="position:absolute;left:0;top:0;width:370px;height:50px;background:#5E6B66;color:#fff;font-weight:bold;font-size:22px;display:flex;align-items:center;padding-left:16px">To do</div>
<div style="position:absolute;left:405px;top:0;width:370px;height:50px;background:#E4572E;color:#fff;font-weight:bold;font-size:22px;display:flex;align-items:center;padding-left:16px">Doing</div>
<div style="position:absolute;left:810px;top:0;width:370px;height:50px;background:#4F8A7B;color:#fff;font-weight:bold;font-size:22px;display:flex;align-items:center;padding-left:16px">Done</div>
<div style="position:absolute;left:16px;top:70px;width:338px;height:80px;background:#fff;border:1px solid #C9D6D1;padding:14px">Weekend rota</div>
<div style="position:absolute;left:16px;top:166px;width:338px;height:80px;background:#fff;border:1px solid #C9D6D1;padding:14px">Refund rule change</div>
<div style="position:absolute;left:421px;top:70px;width:338px;height:100px;background:#fff;border:3px solid #E4572E;padding:14px;font-weight:bold">Login hotfix 4.2.1 (the priority)</div>
<div style="position:absolute;left:826px;top:70px;width:338px;height:80px;background:#fff;border:1px solid #C9D6D1;padding:14px">Courier fallback</div>
<div style="position:absolute;left:826px;top:166px;width:338px;height:80px;background:#fff;border:1px solid #C9D6D1;padding:14px">New-hire training</div>
</div>
```

# A customer's week with a login bug
@noemph defaults
```html
<div style="position:relative;width:1180px;height:490px;font-size:17px">
<svg viewBox="0 0 1180 490" style="position:absolute;left:0;top:0;width:1180px;height:490px">
<line x1="0" y1="250" x2="1180" y2="250" stroke="#C9D6D1" stroke-width="1"/>
<polyline points="147,230 442,420 737,340 1032,150" fill="none" stroke="#1F3A34" stroke-width="4"/>
<circle cx="147" cy="230" r="12" fill="#5E6B66"/>
<circle cx="442" cy="420" r="12" fill="#E4572E"/>
<circle cx="737" cy="340" r="12" fill="#E4572E"/>
<circle cx="1032" cy="150" r="12" fill="#4F8A7B"/>
</svg>
<div style="position:absolute;left:0;top:0;width:285px;height:44px;background:#1F3A34;color:#fff;font-weight:bold;display:flex;align-items:center;justify-content:center">Monday, Update</div>
<div style="position:absolute;left:295px;top:0;width:285px;height:44px;background:#1F3A34;color:#fff;font-weight:bold;display:flex;align-items:center;justify-content:center">Tuesday, Login fails</div>
<div style="position:absolute;left:590px;top:0;width:285px;height:44px;background:#1F3A34;color:#fff;font-weight:bold;display:flex;align-items:center;justify-content:center">Wednesday, Contact</div>
<div style="position:absolute;left:885px;top:0;width:285px;height:44px;background:#1F3A34;color:#fff;font-weight:bold;display:flex;align-items:center;justify-content:center">Friday, Fixed</div>
<div style="position:absolute;left:0;top:54px;width:285px;height:70px;background:#EEF3F1;border:1px solid #C9D6D1;padding:8px;text-align:center">installs 4.2</div>
<div style="position:absolute;left:295px;top:54px;width:285px;height:70px;background:#EEF3F1;border:1px solid #C9D6D1;padding:8px;text-align:center">cannot sign in</div>
<div style="position:absolute;left:590px;top:54px;width:285px;height:70px;background:#EEF3F1;border:1px solid #C9D6D1;padding:8px;text-align:center">waits 2 days for a reply</div>
<div style="position:absolute;left:885px;top:54px;width:285px;height:70px;background:#EEF3F1;border:1px solid #C9D6D1;padding:8px;text-align:center">hotfix works, gets a voucher</div>
<div style="position:absolute;left:0;top:262px;width:285px;text-align:center;font-weight:bold;color:#5E6B66">neutral</div>
<div style="position:absolute;left:295px;top:440px;width:285px;text-align:center;font-weight:bold;color:#E4572E">very negative</div>
<div style="position:absolute;left:590px;top:360px;width:285px;text-align:center;font-weight:bold;color:#E4572E">negative</div>
<div style="position:absolute;left:885px;top:170px;width:285px;text-align:center;font-weight:bold;color:#2F6B5C">positive</div>
</div>
```
