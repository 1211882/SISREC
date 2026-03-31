import { Link } from "react-router-dom";

const nonPersonalized = [
  {
    id: 1,
    title: "Top Restaurants Right Now",
    subtitle: "General list based on global popularity.",
  },
  {
    id: 2,
    title: "This Week's Trends",
    subtitle: "Non-personalized suggestions for all users.",
  },
  {
    id: 3,
    title: "Highly Rated",
    subtitle: "Places with strong recent ratings.",
  },
];

function HomePage() {
  return (
    <section className="hero-panel">
      <div className="hero-copy">
        <p className="eyebrow">Welcome to SISREC</p>
        <h1>Non-personalized recommendations</h1>
        <p className="lead">
          This section shows general recommendations. User personalization
          will be added in a later phase.
        </p>
        <Link className="button solid cta" to="/restaurants">
          View restaurants list
        </Link>
      </div>

      <div className="recommendation-grid">
        {nonPersonalized.map((item, index) => (
          <article
            key={item.id}
            className="recommendation-card"
            style={{ animationDelay: `${index * 80}ms` }}
          >
            <h3>{item.title}</h3>
            <p>{item.subtitle}</p>
            <span className="badge">Coming soon</span>
          </article>
        ))}
      </div>
    </section>
  );
}

export default HomePage;
