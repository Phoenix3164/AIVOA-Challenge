import type { ButtonHTMLAttributes, PropsWithChildren } from 'react'
export function Button({children,className='',type='button',...props}:PropsWithChildren<ButtonHTMLAttributes<HTMLButtonElement>>){return <button type={type} className={`btn ${className}`} {...props}>{children}</button>}
export function Card({children,className=''}:PropsWithChildren<{className?:string}>){return <section className={`card ${className}`}>{children}</section>}
export function Badge({children,tone='blue'}:PropsWithChildren<{tone?:string}>){return <span className={`badge ${tone}`}>{children}</span>}
