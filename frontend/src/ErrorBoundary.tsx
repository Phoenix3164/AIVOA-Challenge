import { Component, type ErrorInfo, type ReactNode } from 'react'

type Props = { children: ReactNode }
type State = { error: Error | null }

export class ErrorBoundary extends Component<Props, State> {
  state: State = { error: null }

  static getDerivedStateFromError(error: Error): State {
    return { error }
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error('PharmaRCA interface error', error, info)
  }

  render() {
    if (this.state.error) {
      return <main style={{padding: 40, fontFamily: 'system-ui', color: '#17263d'}}>
        <h1>Unable to display this investigation</h1>
        <p>The record itself has not been changed. Refresh the page and try the upload again.</p>
        <pre style={{maxWidth: 760, whiteSpace: 'pre-wrap', color: '#9f2d2d', fontSize: 12}}>{this.state.error.message}</pre>
        <button type="button" onClick={() => { this.setState({error: null}); window.location.assign('/investigations/new') }}>Return to the investigation</button>
      </main>
    }
    return this.props.children
  }
}
