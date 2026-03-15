import type { PropsWithChildren, ReactNode } from 'react'

interface CardProps extends PropsWithChildren {
  title?: string
  eyebrow?: string
  actions?: ReactNode
  className?: string
}

export function Card({ title, eyebrow, actions, className, children }: CardProps) {
  return (
    <section className={`card${className ? ` ${className}` : ''}`}>
      {(title || eyebrow || actions) && (
        <header className="card-header">
          <div>
            {eyebrow ? <p className="eyebrow">{eyebrow}</p> : null}
            {title ? <h3>{title}</h3> : null}
          </div>
          {actions ? <div className="card-actions">{actions}</div> : null}
        </header>
      )}
      {children}
    </section>
  )
}
