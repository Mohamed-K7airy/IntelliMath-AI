import React from 'react';
import ReactDOM from 'react-dom/client';
import TeamRevamp from './team_revamp.jsx';

const rootElement = document.getElementById('team-revamp-root');
if (rootElement) {
    ReactDOM.createRoot(rootElement).render(
        <React.StrictMode>
            <TeamRevamp />
        </React.StrictMode>
    );
}
