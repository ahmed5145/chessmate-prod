import React from 'react';
import LegalPage from './LegalPage';

const TermsPage = () => (
  <LegalPage title="Terms of Service (Beta)">
    <p>
      ChessMate is in <strong>beta</strong>. By using the service you agree to these terms.
      We may change features, pricing, or availability without notice during beta.
    </p>
    <h2 className="text-xl font-semibold mt-6 mb-2">Service</h2>
    <p>
      ChessMate imports your chess games, runs engine analysis, and produces batch coaching reports.
      Analysis and coaching are automated; they are not a substitute for human coaching or guaranteed accuracy.
    </p>
    <h2 className="text-xl font-semibold mt-6 mb-2">Accounts & credits</h2>
    <p>
      You are responsible for your account credentials. Credits are consumed when importing games (1 credit per game).
      Batch coach analysis is included once games are on your account. Purchased credits are non-refundable except where required by law.
    </p>
    <h2 className="text-xl font-semibold mt-6 mb-2">Acceptable use</h2>
    <p>
      Do not abuse the API, attempt to access other users&apos; data, or use the service for unlawful purposes.
      We may suspend accounts that violate these rules.
    </p>
    <h2 className="text-xl font-semibold mt-6 mb-2">Disclaimer</h2>
    <p>
      The service is provided &quot;as is&quot; during beta. We do not warrant uninterrupted or error-free operation.
      Limitation of liability applies to the maximum extent permitted by law.
    </p>
    <h2 className="text-xl font-semibold mt-6 mb-2">Contact</h2>
    <p>
      Questions: <a href="mailto:support@chess-mate.online" className="text-indigo-600 hover:underline">support@chess-mate.online</a>
    </p>
    <p className="text-sm opacity-75 mt-8">Last updated: June 2026</p>
  </LegalPage>
);

export default TermsPage;
