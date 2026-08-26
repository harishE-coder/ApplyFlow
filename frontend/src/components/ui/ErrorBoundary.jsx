import React from 'react';
import { AlertTriangle, RefreshCw, Home } from 'lucide-react';
import { Button } from './Button';

export class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null, errorInfo: null };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }

  componentDidCatch(error, errorInfo) {
    console.error('Unhandled React Error:', error, errorInfo);
    this.setState({ errorInfo });
  }

  handleReset = () => {
    this.setState({ hasError: false, error: null, errorInfo: null });
    window.location.reload();
  };

  handleGoHome = () => {
    this.setState({ hasError: false, error: null, errorInfo: null });
    window.location.href = '/dashboard';
  };

  render() {
    if (this.state.hasError) {
      return (
        <div className="min-h-screen w-full flex items-center justify-center bg-[#F6F8FB] p-6">
          <div className="max-w-lg w-full bg-white rounded-3xl border border-[#E2E8F0] shadow-card p-8 text-center space-y-6">
            <div className="w-16 h-16 rounded-2xl bg-[#FEF2F2] text-[#EF4444] border border-[#FECACA] flex items-center justify-center mx-auto shadow-xs">
              <AlertTriangle className="w-8 h-8" />
            </div>

            <div className="space-y-2">
              <h2 className="text-h2 font-extrabold text-[#081226] tracking-tight">
                Something went wrong
              </h2>
              <p className="text-small text-[#64748B]">
                An unexpected interface error occurred. You can reload the page or return to the main dashboard.
              </p>
            </div>

            {this.state.error && (
              <div className="bg-[#F8FAFC] p-4 rounded-xl text-left border border-[#E2E8F0] text-caption font-mono text-[#EF4444] overflow-x-auto max-h-32">
                {this.state.error.toString()}
              </div>
            )}

            <div className="flex items-center justify-center gap-3 pt-2">
              <Button
                variant="primary"
                size="md"
                onClick={this.handleReset}
                className="h-[44px] px-6 gap-2"
              >
                <RefreshCw className="w-4 h-4" />
                Reload Page
              </Button>
              <Button
                variant="outline"
                size="md"
                onClick={this.handleGoHome}
                className="h-[44px] px-6 gap-2"
              >
                <Home className="w-4 h-4" />
                Dashboard
              </Button>
            </div>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}

export default ErrorBoundary;
