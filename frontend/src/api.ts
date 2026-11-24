import axios from 'axios'
import type { Capa, CopilotResponse, Investigation } from './types'
const api=axios.create({baseURL: import.meta.env.VITE_API_URL || 'http://localhost:8000/api'})
export const createInvestigation=async()=> (await api.post<Investigation>('/investigations',{})).data
export const saveInvestigation=async(id:number, fields:Partial<Investigation>)=>{const {title: _generatedTitle,...payload}=fields;return (await api.patch<Investigation>(`/investigations/${id}`,payload)).data}
export const saveCapa=async(id:number, fields:Partial<Capa>)=>(await api.patch<Capa>(`/capa/${id}`,fields)).data
export const getInvestigation=async(id:number)=> (await api.get<Investigation>(`/investigations/${id}`)).data
export const listInvestigations=async()=> (await api.get<Investigation[]>('/investigations')).data
export const downloadReport=async(id:number)=> (await api.get(`/investigations/${id}/report`,{responseType:'blob'})).data as Blob
export const sendCopilot=async(message:string, investigation_id?:number)=>(await api.post<CopilotResponse>('/copilot/message',{message,investigation_id})).data
export const runAnalysis=async(id:number, analysis_type:'rca'|'gaps'|'capa')=>(await api.post<CopilotResponse>(`/investigations/${id}/analyze`,{analysis_type})).data
export const uploadPdf=async(file:File, investigation_id:number)=>{const fd=new FormData();fd.append('file',file);fd.append('investigation_id',String(investigation_id));return (await api.post<CopilotResponse>('/copilot/upload',fd)).data}
export const summary=async()=> (await api.get('/dashboard/summary')).data
export default api
