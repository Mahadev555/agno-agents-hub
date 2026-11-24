const PageHeader = ({ title, description, actions }) => (
  <header className="page-header">
    <div className="page-header-copy">
      <h1 className="page-title">{title}</h1>
      {description && <p className="page-description">{description}</p>}
    </div>
    {actions && (
      <div className="page-header-actions" role="group" aria-label="Page actions">
        {actions}
      </div>
    )}
  </header>
)

export default PageHeader
