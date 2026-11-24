const Settings = ({ user }) => (
  <section className="account-page surface" aria-labelledby="account-details-title">
    <h2 id="account-details-title" className="section-title">Account details</h2>
    <dl className="agent-details-grid">
      <div>
        <dt>Name</dt>
        <dd>{user?.display_name || '—'}</dd>
      </div>
      <div>
        <dt>Email</dt>
        <dd>{user?.email || '—'}</dd>
      </div>
      <div>
        <dt>Access</dt>
        <dd>{user?.is_admin ? 'Administrator' : 'Standard account'}</dd>
      </div>
    </dl>
  </section>
)

export default Settings
