const { useState, useEffect } = React;

function App() {
  const [projects, setProjects] = useState([]);
  const [selectedProject, setSelectedProject] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchProjects();
    setInterval(fetchProjects, 30000); // auto refresh
  }, []);

  async function fetchProjects() {
    setLoading(true);
    const res = await fetch("http://127.0.0.1:5000/api/projects");
    const data = await res.json();
    setProjects(data);
    setLoading(false);
  }

  function getSeverityBadge() {
    const levels = ["critical", "high", "medium", "low"];
    return levels[Math.floor(Math.random() * levels.length)];
  }

  if (selectedProject) {
    return <ProjectDetail project={selectedProject} goBack={() => setSelectedProject(null)} />;
  }

  return (
    <div>
      <header>
        <div>AI Log Analyzer</div>
        <button onClick={fetchProjects}>Refresh</button>
      </header>

      <div className="container">
        <h2>Projects</h2>

        {loading ? <p>Loading...</p> : null}

        <div className="grid">
          {projects.map(p => {
            const severity = getSeverityBadge();
            return (
              <div className="card" key={p.id}>
                <h3>{p.name}</h3>
                <p>Errors: {Math.floor(Math.random() * 500)}</p>

                <span className={`badge ${severity}`}>
                  {severity.toUpperCase()}
                </span>

                <br /><br />

                <button onClick={() => setSelectedProject(p)}>
                  View Details
                </button>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}

function ProjectDetail({ project, goBack }) {
  const [errors, setErrors] = useState([]);

  useEffect(() => {
    loadErrors();
  }, []);

  async function loadErrors() {
    // fake for now
    setErrors([
      { msg: "Database connection failed", type: "DB", severity: "critical", count: 10 },
      { msg: "API timeout", type: "Network", severity: "high", count: 5 }
    ]);
  }

  return (
    <div>
      <header>
        <button onClick={goBack}>⬅ Back</button>
        <div>{project.name}</div>
      </header>

      <div className="container">
        <h2>Errors</h2>

        <table>
          <thead>
            <tr>
              <th>Error</th>
              <th>Type</th>
              <th>Severity</th>
              <th>Count</th>
            </tr>
          </thead>
          <tbody>
            {errors.map((e, i) => (
              <tr key={i}>
                <td>{e.msg}</td>
                <td>{e.type}</td>
                <td>
                  <span className={`badge ${e.severity}`}>
                    {e.severity}
                  </span>
                </td>
                <td>{e.count}</td>
              </tr>
            ))}
          </tbody>
        </table>

        <h2>AI Insights</h2>

        <div className="card">
          <h3>Summary</h3>
          <p>Frequent database failures detected.</p>
        </div>

        <div className="card">
          <h3>Root Causes</h3>
          <ul>
            <li>Connection pool exhausted</li>
            <li>Slow queries</li>
          </ul>
        </div>

        <div className="card">
          <h3>Fixes</h3>
          <ul>
            <li>Increase DB pool size</li>
            <li>Optimize queries</li>
          </ul>
        </div>
      </div>
    </div>
  );
}

ReactDOM.createRoot(document.getElementById("root")).render(
    React.createElement(App)
  );