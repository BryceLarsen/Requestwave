// chordProRenderer.js
// Self-contained ChordPro layout renderer for RequestWave.
// Consumes a chordsheetjs Song object (parsed + transposed) and returns HTML.
// Also provides accidental respelling + music-theory key detection.
// No external imports; safe to import into App.js.

// ---------- accidental respelling (only rewrites accidentals, never naturals) ----------
const CP_SHARP_TO_FLAT = {'C#':'Db','D#':'Eb','F#':'Gb','G#':'Ab','A#':'Bb'};
const CP_FLAT_TO_SHARP = {'Db':'C#','Eb':'D#','Gb':'F#','Ab':'G#','Bb':'A#'};
function cpRespellNote(note, prefer){
  const m = note.match(/^([A-G])([#b]?)$/);
  if(!m) return note;
  const acc=m[2];
  if(!acc) return note;
  if(prefer==='flat'  && acc==='#') return CP_SHARP_TO_FLAT[m[1]+acc] || note;
  if(prefer==='sharp' && acc==='b') return CP_FLAT_TO_SHARP[m[1]+acc] || note;
  return note;
}
function cpRespellChord(chord, prefer){
  if(!chord) return chord;
  return chord.split('/').map(part=>{
    const m = part.match(/^([A-G][#b]?)(.*)$/);
    if(!m) return part;
    return cpRespellNote(m[1], prefer) + m[2];
  }).join('/');
}

// ---------- key detection (dominant key -> label + default accidental) ----------
const CP_NOTES_SHARP=['C','C#','D','D#','E','F','F#','G','G#','A','A#','B'];
const CP_FLAT_OF={'C#':'Db','D#':'Eb','F#':'Gb','G#':'Ab','A#':'Bb'};
const CP_SHARP_KEYS=new Set(['G','D','A','E','B','F#','C#']);
const CP_FLAT_KEYS=new Set(['F','Bb','Eb','Ab','Db','Gb','Cb']);
function cpNoteIndex(note){
  const m=note.match(/^([A-G][#b]?)/); if(!m) return -1;
  let n=m[1]; const F2S={'Db':'C#','Eb':'D#','Gb':'F#','Ab':'G#','Bb':'A#'};
  if(n.length===2&&n[1]==='b') n=F2S[n]||n;
  return CP_NOTES_SHARP.indexOf(n);
}
function cpChordRoot(c){ const m=c.match(/^([A-G][#b]?)/); return m?m[1]:null; }
function cpIsMinor(c){ return /^[A-G][#b]?m(?!aj)/.test(c); }
const CP_MAJOR_SCALE=[0,2,4,5,7,9,11];
const CP_MAJOR_QUAL=['','m','m','','','m','dim'];
function cpKeyChordSet(t){ return CP_MAJOR_SCALE.map((semi,deg)=>({idx:(t+semi)%12, minor:CP_MAJOR_QUAL[deg]==='m'})); }
function cpDetectKey(chords){
  const uniq=[];
  for(const c of chords){ const r=cpChordRoot(c); if(r===null) continue; uniq.push({idx:cpNoteIndex(r), minor:cpIsMinor(c)}); }
  if(!uniq.length) return {tonicIdx:0, prefer:'sharp'};
  let best=null;
  for(let t=0;t<12;t++){
    const set=cpKeyChordSet(t); let score=0;
    for(const ch of uniq){
      const hit=set.find(s=>s.idx===ch.idx && s.minor===ch.minor);
      if(hit) score+=1; else if(set.find(s=>s.idx===ch.idx)) score+=0.3;
    }
    if(uniq.some(ch=>ch.idx===t && !ch.minor)) score+=0.8;
    if(!best||score>best.score) best={t,score};
  }
  const sharpName=CP_NOTES_SHARP[best.t]; const flatName=CP_FLAT_OF[sharpName]||sharpName;
  let prefer;
  if(CP_SHARP_KEYS.has(sharpName)) prefer='sharp';
  else if(CP_FLAT_KEYS.has(flatName)) prefer='flat';
  else prefer='sharp';
  return {tonicIdx:best.t, prefer};
}
function cpKeyLabel(tonicIdx, transpose, prefer){
  const idx=((tonicIdx+transpose)%12+12)%12;
  let name=CP_NOTES_SHARP[idx];
  if(prefer==='flat' && CP_FLAT_OF[name]) name=CP_FLAT_OF[name];
  return name;
}

// helper: collect all chord strings from a chordsheetjs Song (for detection)
function cpCollectChords(song){
  const out=[];
  for(const ln of song.lines) for(const it of ln.items) if(it.chords) out.push(String(it.chords));
  return out;
}

// ---------- layout renderer ----------
function cpEscape(s){ return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;'); }
function cpIsTabLine(line){ if(!line.includes('|')) return false; return /^\s*[a-gA-G][#b]?\s*\|/.test(line) || /\|[-0-9xXhpb/\\~().\s|]{4,}$/.test(line); }
function cpLineToStacks(line, prefer){
  const stacks=[];
  for(const it of line.items){
    if(it.chords===undefined) continue;
    let chord = it.chords ? String(it.chords) : null;
    if(chord && prefer) chord = cpRespellChord(chord, prefer);
    const text = it.lyrics!==undefined ? String(it.lyrics) : '';
    stacks.push({chord:(chord && chord.length)?chord:null, text});
  }
  return stacks;
}
function cpIsChordOnly(stacks){
  const hasChord=stacks.some(s=>s.chord);
  const lyr=stacks.map(s=>s.text).join('').replace(/[.\s]/g,'');
  return hasChord && lyr.length===0;
}
function cpRenderLine(stacks){
  let chars=[];
  for(const st of stacks){
    const chord=st.chord; const text=st.text||'';
    if(text.trim()===''){
      if(chord!==null){ chars.push({ch:'\u2007',chord}); chars.push({ch:'\u2007',chord:null}); chars.push({ch:'\u2007',chord:null}); }
      else if(text.length) chars.push({ch:' ',chord:null});
      continue;
    }
    let placed=false;
    for(let i=0;i<text.length;i++){ let mark=null; if(!placed && chord!==null){ mark=chord; placed=true; } chars.push({ch:text[i],chord:mark}); }
  }
  let s='<div class="cp-line">';
  const emitWord=(u)=>{ let cr='',lr='',col=0; for(const c of u){ if(c.chord) cr+='<span class="cp-c" style="left:'+col+'ch">'+cpEscape(c.chord)+'</span>'; lr+=cpEscape(c.ch); col++; } return '<span class="cp-word"><span class="cp-crow">'+cr+'</span><span class="cp-lrow">'+lr+'</span></span>'; };
  let unit=[]; const flush=()=>{ if(unit.length){ s+=emitWord(unit); unit=[]; } };
  for(const c of chars){ if(c.ch===' '){ flush(); s+='<span class="cp-sp">\u00a0</span>'; } else unit.push(c); }
  flush();
  return s+'</div>';
}
function cpRenderSong(song, prefer){
  let subtitle=null; const blocks=[]; let inChorus=false;
  for(const line of song.lines){
    const tag=line.items.find(it=>it.name!==undefined);
    const isOnlyTag = line.items.length>0 && line.items.every(it=>it.name!==undefined || (it.chords===undefined && it.lyrics===undefined));
    if(tag && isOnlyTag){
      const n=(tag.name||'').toLowerCase();
      if(n==='title') continue;
      if(n==='subtitle'||n==='artist'){ if(!subtitle) subtitle=tag.value; continue; }
      if(n==='start_of_chorus'||n==='soc'){ inChorus=true; continue; }
      if(n==='end_of_chorus'||n==='eoc'){ inChorus=false; continue; }
      if(n==='comment'||n==='c'||n==='tag'){ blocks.push({type:'comment',text:tag.value,chorus:inChorus}); continue; }
      continue;
    }
    const plainText=line.items.map(it=>it.lyrics!==undefined?it.lyrics:'').join('');
    const hasAnyChord=line.items.some(it=>it.chords);
    if(plainText.trim()===''&&!hasAnyChord){ blocks.push({type:'blank',chorus:inChorus}); continue; }
    if(cpIsTabLine(plainText)){ blocks.push({type:'tab',text:plainText,chorus:inChorus}); continue; }
    const stacks=cpLineToStacks(line, prefer);
    if(cpIsChordOnly(stacks)){ blocks.push({type:'chordline',stacks,chorus:inChorus}); continue; }
    if(hasAnyChord){ blocks.push({type:'line',stacks,chorus:inChorus}); continue; }
    blocks.push({type:'plain',text:plainText,chorus:inChorus});
  }
  const cb=[]; let pb=false;
  for(const b of blocks){ const bl=b.type==='blank'; if(bl&&pb)continue; cb.push(b); pb=bl; }
  let html='<div class="cp-sheet">';
  if(subtitle) html+='<div class="cp-sub">'+cpEscape(subtitle)+'</div>';
  const block=(b)=>{
    if(b.type==='blank') return '<div class="cp-blank"></div>';
    if(b.type==='comment') return '<div class="cp-comment">'+cpEscape(b.text)+'</div>';
    if(b.type==='plain') return '<div class="cp-plain">'+cpEscape(b.text)+'</div>';
    if(b.type==='tab') return '<pre class="cp-tab">'+cpEscape(b.text)+'</pre>';
    if(b.type==='chordline'){ let s='<div class="cp-chordline">'; for(const st of b.stacks){ if(st.chord) s+='<span class="cp-conly">'+cpEscape(st.chord)+'</span>'; } return s+'</div>'; }
    return cpRenderLine(b.stacks);
  };
  let i=0;
  while(i<cb.length){
    if(cb[i].chorus){ let run='<div class="cp-chorus">'; while(i<cb.length&&cb[i].chorus){ run+=block(cb[i]); i++; } html+=run+'</div>'; }
    else { html+=block(cb[i]); i++; }
  }
  return html+'</div>';
}

export { cpRenderSong, cpDetectKey, cpKeyLabel, cpCollectChords, cpRespellChord };
