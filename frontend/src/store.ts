import { configureStore, createSlice, type PayloadAction } from '@reduxjs/toolkit'
import type { CopilotResponse, Investigation } from './types'

type Message = { role:'user'|'assistant'; content:string; timestamp:string }
type State = { investigation: Investigation; messages: Message[]; processing:boolean; creatingDraft:boolean; error?:string; notice?:string; fiveWhys:{why:string;answer:string}[]; fishbone:Record<string,string[]>; evidenceGaps:{description:string;rationale:string}[] }
const blank: Investigation = { title:'New RCA Investigation', status:'Draft', severity:'Pending', expected_parameters:{}, actual_parameters:{}, evidence:[], root_causes:[], capa_actions:[], field_metadata:{} }
const initialState: State = { investigation:blank, messages:[{role:'assistant', content:'Describe the deviation or upload a PDF. I will extract reviewable suggestions and keep unknown fields blank.', timestamp:new Date().toISOString()}], processing:false, creatingDraft:false, fiveWhys:[], fishbone:{}, evidenceGaps:[] }

const slice = createSlice({ name:'rca', initialState, reducers: {
  populateInvestigation:(state, action:PayloadAction<Investigation>)=>{ state.investigation={...blank,...action.payload,field_metadata:action.payload.field_metadata||{}}; state.fiveWhys=action.payload.five_whys||[]; state.fishbone=action.payload.fishbone||{}; state.evidenceGaps=action.payload.evidence_gaps||[] },
  resetInvestigation:(state)=>{ state.investigation={...blank}; state.messages=initialState.messages; state.error=undefined; state.notice=undefined; state.fiveWhys=[]; state.fishbone={}; state.evidenceGaps=[] },
  updateInvestigationFields:(state, action:PayloadAction<Partial<Investigation>>)=>{
    const fields=action.payload; state.investigation={...state.investigation,...fields}
    const metadata={...(state.investigation.field_metadata||{})}
    Object.keys(fields).forEach(key=>{ if(!['id','investigation_no','created_at','updated_at','evidence','root_causes','capa_actions','field_metadata'].includes(key)) metadata[key]={source:'human',requires_review:false} })
    state.investigation.field_metadata=metadata
  },
  setDraftCreating:(state, action:PayloadAction<boolean>)=>{state.creatingDraft=action.payload},
  updateCapa:(state, action:PayloadAction<{id:number; changes:Partial<NonNullable<Investigation['capa_actions']>[number]>}>)=>{state.investigation.capa_actions=(state.investigation.capa_actions||[]).map(capa=>capa.id===action.payload.id?{...capa,...action.payload.changes}:capa)},
  setNotice:(state, action:PayloadAction<string|undefined>)=>{state.notice=action.payload}, setError:(state, action:PayloadAction<string|undefined>)=>{state.error=action.payload},
  addMessage:(state, action:PayloadAction<Message>)=>{state.messages.push(action.payload)}, setProcessing:(state, action:PayloadAction<boolean>)=>{state.processing=action.payload},
  applyAi:(state, action:PayloadAction<CopilotResponse>)=>{
    const x=action.payload; const fields=x.fields&&typeof x.fields==='object'?x.fields:{}; const metadata={...(state.investigation.field_metadata||{})}
    Object.entries(fields).forEach(([key,value])=>{ if(metadata[key]?.source!=='human' && value!==undefined && value!==null && value!=='') { (state.investigation as Record<string,unknown>)[key]=value; metadata[key]={source:'ai',requires_review:true} } })
    if(x.investigation){
      Object.entries(x.investigation).forEach(([key,value])=>{ if(metadata[key]?.source!=='human' && key!=='field_metadata' && value!==undefined) (state.investigation as Record<string,unknown>)[key]=value })
      state.investigation.field_metadata={...x.investigation.field_metadata,...metadata}
    } else state.investigation.field_metadata=metadata
    if(x.risk_assessment&&typeof x.risk_assessment==='object') {state.investigation.risk_assessment=x.risk_assessment;state.investigation.severity=x.risk_assessment.level}
    if(Array.isArray(x.root_causes)&&x.root_causes.length)state.investigation.root_causes=x.root_causes
    if(Array.isArray(x.capas)&&x.capas.length)state.investigation.capa_actions=x.capas
    state.fiveWhys=Array.isArray(x.five_whys)?x.five_whys:state.fiveWhys; state.fishbone=x.fishbone&&typeof x.fishbone==='object'?x.fishbone:state.fishbone; state.evidenceGaps=Array.isArray(x.evidence_gaps)?x.evidence_gaps:state.evidenceGaps
  }
} })
export const { populateInvestigation,resetInvestigation,updateInvestigationFields,setDraftCreating,updateCapa,setNotice,setError,addMessage,setProcessing,applyAi }=slice.actions
export const store=configureStore({reducer:{rca:slice.reducer}})
export type RootState=ReturnType<typeof store.getState>
