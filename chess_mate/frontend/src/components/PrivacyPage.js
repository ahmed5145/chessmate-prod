import React from 'react';
import LegalPage from './LegalPage';

const PrivacyPage = () => (
  <LegalPage title="Privacy Policy (Beta)">
    <p>
      ChessMate respects your privacy. This policy describes what we collect and how we use it during the beta.
    </p>
    <h2 className="text-xl font-semibold mt-6 mb-2">What we collect</h2>
    <ul className="list-disc pl-6 space-y-2">
      <li>Account information (email, username) when you register</li>
      <li>Chess games you import (PGN, metadata, analysis results)</li>
      <li>Payment metadata from Stripe (we do not store full card numbers)</li>
      <li>Basic usage logs for reliability and security</li>
    </ul>
    <h2 className="text-xl font-semibold mt-6 mb-2">How we use data</h2>
    <ul className="list-disc pl-6 space-y-2">
      <li>Provide batch analysis and coaching reports</li>
      <li>Operate credits, authentication, and email notifications</li>
      <li>Improve the product and fix errors</li>
    </ul>
    <h2 className="text-xl font-semibold mt-6 mb-2">Sharing</h2>
    <p>
      We use service providers (e.g. AWS hosting, Stripe payments, OpenAI for coaching text, email delivery).
      We do not sell your personal data. Shared batch report links are public only when you explicitly use the share feature.
    </p>
    <h2 className="text-xl font-semibold mt-6 mb-2">Retention & deletion</h2>
    <p>
      We retain account and game data while your account is active. Contact us to request account deletion.
    </p>
    <h2 className="text-xl font-semibold mt-6 mb-2">Contact</h2>
    <p>
      Privacy questions: <a href="mailto:support@chess-mate.online" className="text-indigo-600 hover:underline">support@chess-mate.online</a>
    </p>
    <p className="text-sm opacity-75 mt-8">Last updated: June 2026</p>
  </LegalPage>
);

export default PrivacyPage;
