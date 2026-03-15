interface StatusNoticeProps {
  variant: 'loading' | 'error' | 'empty' | 'success'
  title: string
  detail?: string
}

export function StatusNotice({ variant, title, detail }: StatusNoticeProps) {
  return (
    <div className={`notice notice--${variant}`} role={variant === 'error' ? 'alert' : 'status'}>
      <strong>{title}</strong>
      {detail ? <p>{detail}</p> : null}
    </div>
  )
}
