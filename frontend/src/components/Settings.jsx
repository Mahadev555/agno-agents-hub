const Settings = ({ user }) => (
  <section className="account-page surface" aria-labelledby="account-title">
    <h1 id="account-title" className="section-title">Profile</h1>
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
