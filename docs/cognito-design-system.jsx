import { useState, useEffect } from "react";

const t = {
  bgBase:"#111110",bgSurface:"#1C1C1B",bgSurfaceHover:"#242423",bgSidebar:"#161615",bgElevated:"#272726",
  borderDefault:"#2A2A28",borderStrong:"#3A3A37",borderSubtle:"#1E1E1D",
  textPrimary:"#EDEDEC",textSecondary:"#A1A09A",textTertiary:"#5A5955",textFaded:"#3D3D3A",textOnAccent:"#111110",
  accent:"#E8772E",accentHover:"#D4691F",accentSubtle:"rgba(232,119,46,0.08)",accentGlow:"rgba(232,119,46,0.3)",accentBorder:"rgba(232,119,46,0.5)",
  done:"#5BBC6E",overdue:"#EF5744",
  shadowSm:"0 1px 4px rgba(0,0,0,0.2)",shadowMd:"0 4px 14px rgba(0,0,0,0.3)",shadowLift:"0 6px 20px rgba(0,0,0,0.4)",
};
const sans="'IBM Plex Sans',-apple-system,BlinkMacSystemFont,sans-serif";
const mono="'IBM Plex Mono','Menlo',monospace";
if(!document.getElementById("cog-f")){const l=document.createElement("link");l.id="cog-f";l.href="https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600&family=IBM+Plex+Mono:wght@400;500&display=swap";l.rel="stylesheet";document.head.appendChild(l);}

const projects=[{id:1,name:"PhD",color:"#E8772E"},{id:2,name:"Admin",color:"#5BBC6E"},{id:3,name:"Teaching",color:"#6B9BD2"}];
const pMap=Object.fromEntries(projects.map(p=>[p.id,p]));
const allTasks=[
  {id:1,title:"Submit ethics amendment",desc:"Final submission to ethics board. Compile revised consent forms and updated protocol.",project:1,priority:5,due:"Mar 3",overdue:true,labels:["ethics","admin"],attachments:2,aiTagged:true,bucket:"todo"},
  {id:2,title:"Revise chapter 3",desc:"Full revision — methodology section and literature review update.",project:1,priority:4,due:"Mar 7",labels:["writing"],subtasks:"1/4",bucket:"doing"},
  {id:3,title:"Prepare lab presentation",desc:"Slides covering recent results on ultrasound modality.",project:1,priority:3,due:"Mar 10",labels:["presentation"],attachments:1,bucket:"doing"},
  {id:4,title:"Email supervisor about extension",project:1,priority:2,due:"Mar 12",bucket:"todo"},
  {id:5,title:"Analyze experimental dataset",desc:"Remove outliers, normalize values. Focus on platelet correlations.",project:1,priority:4,due:"In 2 days",labels:["data-analysis"],aiTagged:true,bucket:"todo"},
  {id:6,title:"Clean experimental dataset",desc:"Handle missing values, standardize columns.",project:1,priority:3,due:"Mar 9",labels:["data-analysis"],bucket:"doing"},
  {id:7,title:"Book room for lab meeting",project:2,priority:2,due:"Mar 8",labels:["booking"],done:true,bucket:"done"},
  {id:8,title:"Order lab supplies",project:2,priority:1,due:"Mar 15",bucket:"todo"},
  {id:9,title:"Complete TA form",desc:"Fill out hours and submit.",project:2,priority:3,due:"Mar 14",labels:["admin"],bucket:"todo"},
  {id:10,title:"Grade midterm papers",desc:"30 papers, use rubric from last semester.",project:3,priority:3,due:"Mar 14",labels:["grading"],subtasks:"12/30",bucket:"doing"},
  {id:11,title:"Prepare tutorial materials",project:3,priority:2,due:"Mar 11",labels:["teaching"],bucket:"todo"},
  {id:12,title:"Schedule advisor meeting",desc:"Progress update meeting for next week.",project:1,priority:2,due:"Tomorrow",aiTagged:true,bucket:"todo"},
];
const bkts=[{id:"todo",title:"To Do"},{id:"doing",title:"In Progress"},{id:"done",title:"Done"}];
const priC=[,"#5BBC6E","#5BBC6E","#E2C541","#E8772E","#EF5744"];

function Bubble({task,expanded,onToggle,kanban}){
  const[hov,setHov]=useState(false);const p=task.priority||0;const proj=pMap[task.project];
  const presO=task.done?.35:p>=4?1:p===3?.85:p===2?.65:.45;
  const titleC=task.done?t.textTertiary:p>=4?t.textPrimary:p===3?"#C8C8C6":t.textSecondary;
  return(
    <div onMouseEnter={()=>setHov(true)} onMouseLeave={()=>setHov(false)}
      onClick={e=>{e.stopPropagation();onToggle?.(task.id);}}
      style={{position:"relative",background:expanded?t.bgElevated:t.bgSurface,border:`1px solid ${expanded?t.borderStrong:task.aiTagged?t.accentBorder:hov?t.borderStrong:t.borderDefault}`,borderRadius:10,padding:expanded?"18px 20px":kanban?"10px 12px":"14px 16px",cursor:"pointer",boxShadow:task.aiTagged&&!expanded?`${shadow(p)}, inset 0 0 12px -4px ${t.accentGlow}`:hov&&!expanded?t.shadowLift:shadow(p),transform:hov&&!expanded?"translateY(-1px)":"translateY(0)",transition:"transform 200ms ease-out, box-shadow 200ms ease-out, border-color 200ms ease-out",opacity:presO,width:kanban?"100%":expanded?360:200,minHeight:kanban?void 0:expanded?void 0:90,maxWidth:kanban?"100%":expanded?400:200,overflow:"hidden",display:"flex",flexDirection:"column"}}>
      {proj&&!kanban&&<div style={{position:"absolute",top:0,right:0,width:0,height:0,borderLeft:"18px solid transparent",borderTop:`18px solid ${proj.color}`,borderTopRightRadius:9,opacity:expanded?.6:.3,transition:"opacity 200ms"}}/>}
      <div style={{fontSize:kanban&&!expanded?13.5:expanded?16:14.5,fontWeight:p>=4?500:400,fontFamily:sans,color:titleC,textDecoration:task.done?"line-through":"none",lineHeight:1.4,letterSpacing:"-0.01em",marginBottom:expanded?12:0,display:expanded?"block":"-webkit-box",WebkitLineClamp:expanded?void 0:kanban?2:3,WebkitBoxOrient:"vertical",overflow:expanded?"visible":"hidden",paddingRight:!kanban&&!expanded?14:0}}>{task.title}</div>
      {!expanded&&!kanban&&<div style={{flex:1}}/>}
      {hov&&!expanded&&<div style={{display:"flex",gap:8,alignItems:"center",flexWrap:"wrap",animation:"fadeIn 100ms ease-out",marginTop:kanban?4:0,minHeight:20}}>
        {task.due&&<span style={{fontSize:12,color:task.overdue?t.overdue:t.textTertiary,fontFamily:sans}}>{task.due}</span>}
        {task.labels?.[0]&&<span style={{fontSize:11.5,color:t.textTertiary,fontFamily:sans}}>{task.labels[0]}</span>}
        {task.attachments&&<span style={{fontSize:11.5,color:t.textTertiary}}>📎{task.attachments}</span>}
        {task.subtasks&&<span style={{fontSize:11.5,color:t.textTertiary}}>☐ {task.subtasks}</span>}
      </div>}
      {expanded&&<div style={{animation:"expandIn 200ms ease-out"}}>
        {task.desc&&<div style={{fontSize:13.5,color:t.textSecondary,lineHeight:1.55,fontFamily:sans,marginBottom:14}}>{task.desc}</div>}
        <div style={{display:"flex",flexWrap:"wrap",gap:6,marginBottom:12,alignItems:"center"}}>
          <div style={{display:"flex",gap:3,marginRight:6}}>{[1,2,3,4,5].map(i=><div key={i} style={{width:7,height:7,borderRadius:"50%",background:i<=p?priC[p]:t.borderDefault}}/>)}</div>
          <span style={{fontSize:12.5,color:task.overdue?t.overdue:t.textTertiary,fontFamily:sans}}>{task.due}</span>
          {proj&&<span style={{fontSize:12,color:proj.color,fontFamily:sans,opacity:.7}}>{proj.name}</span>}
          {task.labels?.map((l,i)=><span key={i} style={{fontSize:11.5,fontWeight:500,fontFamily:sans,color:t.textSecondary,background:t.bgSurfaceHover,borderRadius:9999,padding:"2px 8px"}}>{l}</span>)}
          {task.attachments&&<span style={{fontSize:12,color:t.textTertiary}}>📎 {task.attachments}</span>}
          {task.subtasks&&<span style={{fontSize:12,color:t.textTertiary}}>☐ {task.subtasks}</span>}
        </div>
        <div style={{display:"flex",gap:8}}><Btn c={t.done}>✓ Done</Btn><Btn>Edit</Btn></div>
      </div>}
    </div>);
}
function shadow(p){return p>=4?t.shadowMd:t.shadowSm;}
function Btn({children,c}){const[h,setH]=useState(false);return <button onMouseEnter={()=>setH(true)} onMouseLeave={()=>setH(false)} style={{fontSize:12.5,fontFamily:sans,fontWeight:500,color:c||t.textTertiary,background:h?t.bgSurfaceHover:"none",border:`1px solid ${t.borderDefault}`,borderRadius:6,padding:"4px 10px",cursor:"pointer",transition:"all 120ms"}}>{children}</button>;}

function Cluster({project,tasks,expanded,onToggle}){
  const active=[...tasks].filter(x=>!x.done).sort((a,b)=>(b.priority||0)-(a.priority||0));
  const done=tasks.filter(x=>x.done);const[sd,setSd]=useState(false);
  return(<div style={{marginBottom:44}}>
    <div style={{display:"flex",alignItems:"center",gap:8,marginBottom:14,paddingLeft:2}}>
      <div style={{width:8,height:8,borderRadius:"50%",background:project.color}}/><span style={{fontSize:12,fontWeight:600,fontFamily:sans,color:t.textTertiary,textTransform:"uppercase",letterSpacing:"0.07em"}}>{project.name}</span><span style={{fontSize:12,fontFamily:sans,color:t.textFaded}}>{active.length}</span>
    </div>
    <div style={{display:"flex",flexWrap:"wrap",gap:12,alignItems:"flex-start",alignContent:"flex-start"}}>{active.map(task=><Bubble key={task.id} task={task} expanded={expanded===task.id} onToggle={onToggle}/>)}</div>
    {done.length>0&&<><button onClick={()=>setSd(!sd)} style={{fontSize:12,fontFamily:sans,color:t.textTertiary,background:"none",border:"none",cursor:"pointer",marginTop:14,padding:0,opacity:.5}}>{sd?"▾":"▸"} {done.length} completed</button>
    {sd&&<div style={{display:"flex",flexWrap:"wrap",gap:10,marginTop:10}}>{done.map(task=><Bubble key={task.id} task={task} expanded={expanded===task.id} onToggle={onToggle}/>)}</div>}</>}
  </div>);
}

function Kanban({tasks,expanded,onToggle,anim}){
  return(<div style={{display:"flex",gap:14,padding:"0 24px",overflowX:"auto",flex:1,alignItems:"flex-start"}}>
    {bkts.map((b,ci)=>{const bt=tasks.filter(x=>x.bucket===b.id);return(
      <div key={b.id} style={{flex:"0 0 280px",display:"flex",flexDirection:"column"}}>
        <div style={{fontSize:13,fontWeight:600,fontFamily:sans,color:t.textTertiary,textTransform:"uppercase",letterSpacing:"0.05em",padding:"0 4px 10px",display:"flex",justifyContent:"space-between",opacity:anim>=1?1:0,transition:"opacity 250ms ease-out",transitionDelay:`${ci*80}ms`}}><span>{b.title}</span><span style={{opacity:.4}}>{bt.length}</span></div>
        <div style={{display:"flex",flexDirection:"column",gap:8,background:anim>=1?t.bgBase:"transparent",borderRadius:10,padding:anim>=1?8:0,border:anim>=1?`1px solid ${t.borderSubtle}`:"1px solid transparent",minHeight:120,flex:1,opacity:anim>=1?1:0,transition:"all 300ms ease-out",transitionDelay:`${ci*80}ms`}}>
          {bt.map((task,i)=>{const d=150+ci*80+i*50;return(
            <div key={task.id} style={{opacity:anim>=2?1:0,transform:anim>=2?"translateY(0) scale(1)":"translateY(-12px) scale(0.92)",transition:"all 300ms cubic-bezier(0.2,0.8,0.2,1)",transitionDelay:`${d}ms`}}>
              <Bubble task={task} expanded={expanded===task.id} onToggle={onToggle} kanban/>
            </div>);})}
        </div>
      </div>);})}
  </div>);
}

function List({tasks,onToggle}){
  const s=[...tasks].filter(x=>!x.done).sort((a,b)=>(b.priority||0)-(a.priority||0));
  return(<div style={{padding:"0 24px"}}>{s.map(task=>{const p=task.priority||0;return(
    <div key={task.id} onClick={()=>onToggle(task.id)} style={{display:"flex",alignItems:"center",gap:14,padding:"8px 12px",borderBottom:`1px solid ${t.borderSubtle}`,cursor:"pointer",transition:"background 100ms"}}
      onMouseEnter={e=>e.currentTarget.style.background=t.bgSurfaceHover} onMouseLeave={e=>e.currentTarget.style.background="transparent"}>
      <div style={{display:"flex",gap:2}}>{[1,2,3,4,5].map(i=><div key={i} style={{width:5,height:5,borderRadius:"50%",background:i<=p?priC[p]:t.borderDefault}}/>)}</div>
      <span style={{flex:1,fontSize:14,fontFamily:sans,fontWeight:p>=4?500:400,color:p>=3?t.textPrimary:t.textSecondary,overflow:"hidden",textOverflow:"ellipsis",whiteSpace:"nowrap"}}>{task.title}</span>
      {task.labels?.[0]&&<span style={{fontSize:11.5,color:t.textTertiary,fontFamily:sans}}>{task.labels[0]}</span>}
      <span style={{fontSize:12.5,color:task.overdue?t.overdue:t.textTertiary,fontFamily:sans,whiteSpace:"nowrap"}}>{task.due}</span>
    </div>);})}</div>);
}

function Extract(){
  const[ps,setPs]=useState([]);const[st,setSt]=useState(false);const[exp,setExp]=useState(null);const[sr,setSr]=useState(false);
  const mk=[{id:101,title:"Revise introduction section",project:1,priority:4,due:"Mar 7",labels:["writing"],aiTagged:true,bucket:"todo"},{id:102,title:"Run stats on cohort B",project:1,priority:3,due:"Mar 9",labels:["data-analysis"],aiTagged:true,bucket:"todo"},{id:103,title:"Book conference room Thursday",project:2,priority:2,due:"Mar 6",labels:["booking"],aiTagged:true,bucket:"todo"}];
  const go=()=>{setPs([]);setSt(true);mk.forEach((p,i)=>setTimeout(()=>{setPs(v=>[...v,p]);if(i===mk.length-1)setSt(false);},500+i*450));};
  return(<div style={{padding:"32px 24px",maxWidth:660,margin:"0 auto"}}>
    <div style={{fontSize:20,fontWeight:600,fontFamily:sans,color:t.accent,marginBottom:24,letterSpacing:"-0.02em"}}>◆ Extract Thoughts</div>
    <textarea defaultValue="I had a meeting with my supervisor today. We agreed I need to revise the introduction by Friday and run the stats on cohort B by next week. Also need to book a room for Thursday." rows={4} style={{width:"100%",padding:"12px 14px",fontSize:15,fontFamily:sans,color:t.textPrimary,background:t.bgElevated,border:`1px solid ${t.borderDefault}`,borderRadius:10,outline:"none",resize:"vertical",lineHeight:1.55}}/>
    <div style={{display:"flex",justifyContent:"flex-end",marginTop:14,gap:10,alignItems:"center"}}>
      <kbd style={{fontSize:11.5,fontFamily:mono,color:t.textTertiary,background:t.bgElevated,border:`1px solid ${t.borderDefault}`,borderRadius:5,padding:"2px 6px"}}>Ctrl+↵</kbd>
      <button onClick={go} style={{height:40,padding:"0 18px",fontSize:14,fontWeight:500,fontFamily:sans,background:st?t.accentHover:t.accent,color:t.textOnAccent,border:"none",borderRadius:8,cursor:"pointer",display:"flex",alignItems:"center",gap:7}}>
        {st&&<span style={{animation:"spin 0.8s linear infinite",display:"inline-flex"}}><svg width={15} height={15} viewBox="0 0 15 15" fill="none"><circle cx={7.5} cy={7.5} r={6} stroke="currentColor" strokeWidth={1.5} opacity={.25}/><path d="M13.5 7.5a6 6 0 0 0-6-6" stroke="currentColor" strokeWidth={1.5} strokeLinecap="round"/></svg></span>}◆ Extract</button>
    </div>
    {ps.length>0&&<button onClick={()=>setSr(!sr)} style={{display:"flex",alignItems:"center",gap:6,background:"none",border:"none",color:t.textTertiary,fontSize:12.5,fontFamily:sans,cursor:"pointer",padding:0,marginTop:20}}><span style={{transform:sr?"rotate(90deg)":"rotate(0)",transition:"transform 150ms",fontSize:9}}>▶</span> Raw response</button>}
    {sr&&<pre style={{marginTop:8,padding:14,background:t.bgBase,border:`1px solid ${t.borderDefault}`,borderRadius:8,fontSize:12,fontFamily:mono,color:t.textTertiary,lineHeight:1.5,overflow:"auto",maxHeight:180}}>{`{ "model": "gemini-2.0-flash", "proposals": ${ps.length} }`}</pre>}
    {ps.length>0&&<>
      <div style={{display:"flex",alignItems:"center",gap:10,margin:"20px 0 16px",color:t.textTertiary,fontSize:13,fontFamily:sans}}><span style={{height:1,width:16,background:t.borderDefault}}/>{ps.length} thoughts extracted<span style={{flex:1,height:1,background:t.borderDefault}}/></div>
      <div style={{display:"flex",flexWrap:"wrap",gap:12}}>{ps.map((p,i)=><div key={p.id} style={{animation:`bubbleIn 280ms ${i*100}ms both`}}><Bubble task={p} expanded={exp===p.id} onToggle={setExp}/></div>)}</div>
      <div style={{display:"flex",justifyContent:"flex-end",gap:10,marginTop:20}}>
        <button style={{fontSize:13.5,fontFamily:sans,fontWeight:500,color:t.textTertiary,background:"none",border:`1px solid ${t.borderDefault}`,borderRadius:8,padding:"8px 14px",cursor:"pointer"}}>Reject</button>
        <button style={{fontSize:13.5,fontFamily:sans,fontWeight:500,color:t.textOnAccent,background:t.accent,border:"none",borderRadius:8,padding:"8px 18px",cursor:"pointer"}}>Approve All ({ps.length})</button>
      </div>
    </>}
  </div>);
}

function Side({view,setView,proj,setProj}){
  const[hov,setHov]=useState(null);
  const NI=({id,label,count,cc,onClick})=>{const a=view===id&&!proj;const h=hov===id;return <button onClick={onClick} onMouseEnter={()=>setHov(id)} onMouseLeave={()=>setHov(null)} style={{display:"flex",alignItems:"center",justifyContent:"space-between",width:"100%",padding:"7px 12px",borderRadius:7,border:"none",background:a?t.accentSubtle:h?t.bgSurfaceHover:"transparent",cursor:"pointer",transition:"all 100ms"}}><span style={{fontSize:13.5,fontFamily:sans,fontWeight:a?500:400,color:a?t.accent:h?t.textPrimary:t.textSecondary}}>{label}</span>{count!=null&&<span style={{fontSize:12,fontFamily:sans,fontWeight:500,color:cc||t.textTertiary}}>{count}</span>}</button>;};
  return(<div style={{width:200,background:t.bgSidebar,borderRight:`1px solid ${t.borderSubtle}`,display:"flex",flexDirection:"column",padding:"20px 0",flexShrink:0,height:"100%"}}>
    <div style={{padding:"0 16px",marginBottom:28}}><span style={{fontSize:17,fontWeight:600,fontFamily:sans,color:t.textPrimary,letterSpacing:"-0.04em"}}>cognito</span></div>
    <div style={{display:"flex",flexDirection:"column",gap:1,padding:"0 6px"}}>
      <NI id="all" label="All Thoughts" count={allTasks.filter(x=>!x.done).length} onClick={()=>{setView("all");setProj(null);}}/>
      <NI id="upcoming" label="Upcoming" count={3} onClick={()=>{setView("upcoming");setProj(null);}}/>
      <NI id="overdue" label="Overdue" count={1} cc={t.overdue} onClick={()=>{setView("overdue");setProj(null);}}/>
    </div>
    <div style={{padding:"0 16px",marginTop:28,marginBottom:10}}><span style={{fontSize:11,fontWeight:600,fontFamily:sans,color:t.textTertiary,textTransform:"uppercase",letterSpacing:"0.08em"}}>Projects</span></div>
    <div style={{display:"flex",flexDirection:"column",gap:1,padding:"0 6px"}}>{projects.map(p=><button key={p.id} onMouseEnter={()=>setHov(`p${p.id}`)} onMouseLeave={()=>setHov(null)} onClick={()=>{setProj(p.id);setView("project");}} style={{display:"flex",alignItems:"center",gap:9,padding:"7px 12px",borderRadius:7,border:"none",width:"100%",cursor:"pointer",background:proj===p.id?t.accentSubtle:hov===`p${p.id}`?t.bgSurfaceHover:"transparent",transition:"all 100ms"}}><div style={{width:7,height:7,borderRadius:"50%",background:p.color}}/><span style={{fontSize:13.5,fontFamily:sans,color:proj===p.id?t.accent:t.textSecondary,flex:1,textAlign:"left"}}>{p.name}</span><span style={{fontSize:12,fontFamily:sans,color:t.textTertiary}}>{allTasks.filter(x=>x.project===p.id&&!x.done).length}</span></button>)}</div>
    <div style={{flex:1}}/>
    <div style={{padding:"0 6px"}}><button onMouseEnter={()=>setHov("ext")} onMouseLeave={()=>setHov(null)} onClick={()=>{setView("extract");setProj(null);}} style={{display:"flex",alignItems:"center",gap:8,padding:"9px 12px",borderRadius:8,border:`1px solid ${t.accent}25`,width:"100%",background:view==="extract"?t.accentSubtle:hov==="ext"?t.bgSurfaceHover:t.accentSubtle,cursor:"pointer",transition:"all 100ms"}}><span style={{color:t.accent,fontSize:13.5,fontFamily:sans,fontWeight:600}}>◆ Extract</span></button></div>
    <div style={{padding:"12px 16px",marginTop:8,borderTop:`1px solid ${t.borderSubtle}`}}><span style={{fontSize:12,fontFamily:sans,color:t.textTertiary}}>you@email.com</span></div>
  </div>);
}

export default function App(){
  const[view,setView]=useState("all");const[proj,setProj]=useState(null);const[exp,setExp]=useState(null);const[pv,setPv]=useState("kanban");const[anim,setAnim]=useState(3);
  const toggle=id=>setExp(prev=>prev===id?null:id);
  useEffect(()=>{if(view==="project"&&pv==="kanban"){setAnim(0);const a=setTimeout(()=>setAnim(1),50);const b=setTimeout(()=>setAnim(2),200);const c=setTimeout(()=>setAnim(3),800);return()=>{clearTimeout(a);clearTimeout(b);clearTimeout(c);}}},[proj,pv,view]);
  const pt=proj?allTasks.filter(x=>x.project===proj):[];const po=proj?pMap[proj]:null;
  return(<div style={{background:t.bgBase,minHeight:"100vh",fontFamily:sans,color:t.textPrimary,display:"flex"}} onClick={()=>setExp(null)}>
    <style>{`@keyframes fadeIn{from{opacity:0}to{opacity:1}}@keyframes expandIn{from{opacity:0;transform:translateY(-4px)}to{opacity:1;transform:translateY(0)}}@keyframes spin{to{transform:rotate(360deg)}}@keyframes bubbleIn{from{opacity:0;transform:scale(.92) translateY(8px)}to{opacity:1;transform:scale(1) translateY(0)}}*{box-sizing:border-box;margin:0}::placeholder{color:${t.textTertiary}}::-webkit-scrollbar{width:6px}::-webkit-scrollbar-track{background:transparent}::-webkit-scrollbar-thumb{background:${t.borderDefault};border-radius:3px}`}</style>
    <Side view={view} setView={v=>{setView(v);setExp(null);setPv("kanban");}} proj={proj} setProj={p=>{setProj(p);setView("project");setExp(null);setPv("kanban");}}/>
    <div style={{flex:1,display:"flex",flexDirection:"column",overflow:"hidden"}}>
      <div style={{display:"flex",alignItems:"center",padding:"12px 24px",borderBottom:`1px solid ${t.borderSubtle}`,gap:10,flexShrink:0}}>
        <span style={{fontSize:18,fontWeight:600,letterSpacing:"-0.02em",marginRight:"auto",display:"flex",alignItems:"center",gap:8}}>
          {view==="extract"?"Extract":proj?<><div style={{width:8,height:8,borderRadius:"50%",background:po?.color}}/>{po?.name}</>:"All Thoughts"}
        </span>
        {view==="project"&&<div style={{display:"flex",gap:2,marginRight:8}}>{["kanban","list"].map(m=><button key={m} onClick={()=>setPv(m)} style={{fontSize:12.5,fontFamily:sans,fontWeight:500,padding:"5px 11px",borderRadius:6,border:"none",cursor:"pointer",color:pv===m?t.accent:t.textTertiary,background:pv===m?t.accentSubtle:"transparent",transition:"all 150ms",textTransform:"capitalize"}}>{m}</button>)}</div>}
        <input placeholder="Search..." style={{height:32,padding:"0 12px",fontSize:13,fontFamily:sans,color:t.textPrimary,background:t.bgElevated,border:`1px solid ${t.borderDefault}`,borderRadius:7,outline:"none",width:160}}/>
      </div>
      <div style={{flex:1,overflowY:"auto",padding:view==="extract"?0:"24px 0 24px 24px"}}>
        {view==="extract"?<Extract/>:view==="project"&&pv==="kanban"?<Kanban tasks={pt} expanded={exp} onToggle={toggle} anim={anim}/>:view==="project"&&pv==="list"?<List tasks={pt} onToggle={toggle}/>:projects.map(p=><Cluster key={p.id} project={p} tasks={allTasks.filter(x=>x.project===p.id)} expanded={exp} onToggle={toggle}/>)}
      </div>
    </div>
  </div>);
}