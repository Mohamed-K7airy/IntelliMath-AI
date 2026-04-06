import React, { Suspense } from 'react';
import ReactDOM from 'react-dom/client';
import Lanyard from './components/Lanyard/Lanyard';
import ProfileCard from './components/ProfileCard/ProfileCard';
import ShinyText from './components/ShinyText/ShinyText';

class TeamErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false };
  }
  static getDerivedStateFromError(error) {
    return { hasError: true };
  }
  render() {
    if (this.state.hasError) {
      return (
        <div style={{ color: '#E0702E', textAlign: 'center', padding: '100px', fontSize: '1.2rem', fontFamily: 'monospace' }}>
          ⚠️ Partially failed to load 3D team assets over the network. Please refresh.
        </div>
      );
    }
    return this.props.children; 
  }
}

const mohamedData = {
  id: 1,
  name: "Mohamed Khairy",
  role: "Frontend + DBM + AI",
  handle: "K7airy",
  avatar: "/team/mohamed_final_transparent.png",
  status: "Online",
  bio: "Frontend Developer specializing in modern, responsive web applications with Supabase integration and AI capabilities, delivering intelligent, user-friendly experiences."
};

const secondMemberData = {
  id: 2,
  name: "Youssef Moustafa",
  role: "AI Engineer",
  handle: "Youssef",
  avatar: "/team/youssef.png",
  status: "Online",
  bio: "AI Engineer focused on developing, training, and optimizing machine learning models, including large language models (LLMs), to build intelligent and data-driven applications."
};

const thirdMemberData = {
  id: 3,
  name: "Jousha Adel",
  role: "AI Engineer",
  handle: "Joushoa",
  avatar: "/team/jousha.png",
  status: "Online",
  bio: "AI Engineer specializing in developing and optimizing predictive models, generative AI, and advanced neural architectures to build intelligent solutions."
};

const fourthMemberData = {
  id: 4,
  name: "Mina Adly",
  role: "Backend Developer",
  handle: "Mina",
  avatar: "/team/mina.png",
  status: "Online",
  bio: "Backend Developer responsible for developing APIs, and ensuring seamless communication between frontend and backend systems."
};

const TeamRevamp = () => {
  return (
    <TeamErrorBoundary>
      <Suspense fallback={<div style={{ color: 'white', textAlign: 'center', padding: '100px' }}>Loading Team 3D Assets...</div>}>
      <div className="single-profile-container">
        {/* First Profile */}
        <div className="single-profile-row">
          {/* Information Column (Left) */}
          <div className="single-info-column">
            <div className="single-info-content">
              <h1 className="about-me-heading">
                <ShinyText text="Mohamed Khairy" speed={3} />
              </h1>
              <p className="single-bio">{mohamedData.bio}</p>

              <div className="single-stats-container">
                <div className="single-stat">
                  <span className="single-stat-num">5<span className="accent">+</span></span>
                  <span className="single-stat-lab">Total Projects</span>
                </div>
                <div className="single-stat">
                  <span className="single-stat-num">2</span>
                  <span className="single-stat-lab">Years Experience</span>
                </div>
                <div className="single-stat">
                  <span className="single-stat-num">2.9<span className="accent">+</span></span>
                  <span className="single-stat-lab">GPA</span>
                </div>
              </div>
            </div>
          </div>

          {/* 3D Visual Column (Right) */}
          <div className="single-lanyard-column">
            <div className="team-member-card-wrapper">
              <Lanyard position={[0, 0, 25]} gravity={[0, -40, 0]}>
                <ProfileCard
                  name={mohamedData.name}
                  title={mohamedData.role}
                  handle={mohamedData.handle}
                  avatarUrl={mohamedData.avatar}
                  status={mohamedData.status}
                  showUserInfo={true}
                  enableTilt={false}
                  showBehindGradient={true}
                  innerGradient="linear-gradient(180deg, #1C0F0A 0%, #000 100%)"
                  className="new-profile-card"
                />
              </Lanyard>
            </div>
          </div>
        </div>

        <div style={{ padding: '30px 0' }}></div> {/* Spacing divider */}

        {/* Second Profile (Reversed) */}
        <div className="single-profile-row reverse">
          {/* Information Column (Right) */}
          <div className="single-info-column">
            <div className="single-info-content">
              <h1 className="about-me-heading">
                <ShinyText text="Youssef Moustafa" speed={3} />
              </h1>
              <p className="single-bio">{secondMemberData.bio}</p>

              <div className="single-stats-container">
                <div className="single-stat">
                  <span className="single-stat-num">6<span className="accent">+</span></span>
                  <span className="single-stat-lab">Total Projects</span>
                </div>
                <div className="single-stat">
                  <span className="single-stat-num">2</span>
                  <span className="single-stat-lab">Years Experience</span>
                </div>
                <div className="single-stat">
                  <span className="single-stat-num">3.5<span className="accent">+</span></span>
                  <span className="single-stat-lab">GPA</span>
                </div>
              </div>
            </div>
          </div>

          {/* 3D Visual Column (Left) */}
          <div className="single-lanyard-column">
            <div className="team-member-card-wrapper">
              <Lanyard position={[0, 0, 25]} gravity={[0, -40, 0]}>
                <ProfileCard
                  name={secondMemberData.name}
                  title={secondMemberData.role}
                  handle={secondMemberData.handle}
                  avatarUrl={secondMemberData.avatar}
                  status={secondMemberData.status}
                  showUserInfo={true}
                  enableTilt={false}
                  showBehindGradient={true}
                  innerGradient="linear-gradient(180deg, #1C0F0A 0%, #000 100%)"
                  className="new-profile-card"
                />
              </Lanyard>
            </div>
          </div>
        </div>

        <div style={{ padding: '30px 0' }}></div> {/* Spacing divider */}

        {/* Third Profile (Standard) */}
        <div className="single-profile-row">
          {/* Information Column (Left) */}
          <div className="single-info-column">
            <div className="single-info-content">
              <h1 className="about-me-heading">
                <ShinyText text="Jousha Adel" speed={3} />
              </h1>
              <p className="single-bio">{thirdMemberData.bio}</p>

              <div className="single-stats-container">
                <div className="single-stat">
                  <span className="single-stat-num">5<span className="accent">+</span></span>
                  <span className="single-stat-lab">Total Projects</span>
                </div>
                <div className="single-stat">
                  <span className="single-stat-num">2</span>
                  <span className="single-stat-lab">Years Experience</span>
                </div>
                <div className="single-stat">
                  <span className="single-stat-num">2.9<span className="accent">+</span></span>
                  <span className="single-stat-lab">GPA</span>
                </div>
              </div>
            </div>
          </div>

          {/* 3D Visual Column (Right) */}
          <div className="single-lanyard-column">
            <div className="team-member-card-wrapper">
              <Lanyard position={[0, 0, 25]} gravity={[0, -40, 0]}>
                <ProfileCard
                  name={thirdMemberData.name}
                  title={thirdMemberData.role}
                  handle={thirdMemberData.handle}
                  avatarUrl={thirdMemberData.avatar}
                  status={thirdMemberData.status}
                  showUserInfo={true}
                  enableTilt={false}
                  showBehindGradient={false}
                  innerGradient="linear-gradient(180deg, #111729 0%, #000 100%)"
                  className="new-profile-card"
                />
              </Lanyard>
            </div>
          </div>
        </div>

        <div style={{ padding: '30px 0' }}></div> {/* Spacing divider */}

        {/* Fourth Profile (Reversed) */}
        <div className="single-profile-row reverse">
          {/* Information Column (Right) */}
          <div className="single-info-column">
            <div className="single-info-content">
              <h1 className="about-me-heading">
                <ShinyText text="Mina Adly" speed={3} />
              </h1>
              <p className="single-bio">{fourthMemberData.bio}</p>

              <div className="single-stats-container">
                <div className="single-stat">
                  <span className="single-stat-num">1<span className="accent">+</span></span>
                  <span className="single-stat-lab">Total Projects</span>
                </div>
                <div className="single-stat">
                  <span className="single-stat-num">2</span>
                  <span className="single-stat-lab">Year Experience</span>
                </div>
                <div className="single-stat">
                  <span className="single-stat-num">2.8<span className="accent">+</span></span>
                  <span className="single-stat-lab">GPA</span>
                </div>
              </div>
            </div>
          </div>

          {/* 3D Visual Column (Left) */}
          <div className="single-lanyard-column">
            <div className="team-member-card-wrapper">
              <Lanyard position={[0, 0, 25]} gravity={[0, -40, 0]}>
                <ProfileCard
                  name={fourthMemberData.name}
                  title={fourthMemberData.role}
                  handle={fourthMemberData.handle}
                  avatarUrl={fourthMemberData.avatar}
                  status={fourthMemberData.status}
                  showUserInfo={true}
                  enableTilt={false}
                  showBehindGradient={false}
                  innerGradient="linear-gradient(180deg, #111729 0%, #000 100%)"
                  className="new-profile-card"
                />
              </Lanyard>
            </div>
          </div>
        </div>

      </div>
    </Suspense>
    </TeamErrorBoundary>
  );
};



export default TeamRevamp;
