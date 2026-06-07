import React, { useEffect, useState } from 'react';
import LegalPage, { LegalLink } from './LegalPage';
import api from '../services/api';

const TermsPage = () => {
  const [legal, setLegal] = useState({
    legal_entity_name: '',
    legal_entity_incorporated: false,
    legal_governing_law: 'the State of Delaware, United States',
    legal_entity_address: '',
    support_email: 'support@chess-mate.online',
  });

  useEffect(() => {
    api.get('/api/v1/public/site-config/')
      .then((response) => {
        const data = response.data || {};
        setLegal((prev) => ({
          ...prev,
          legal_entity_name: data.legal_entity_name || '',
          legal_entity_incorporated: Boolean(data.legal_entity_incorporated),
          legal_governing_law: data.legal_governing_law || prev.legal_governing_law,
          legal_entity_address: data.legal_entity_address || '',
          support_email: data.support_email || prev.support_email,
        }));
      })
      .catch(() => {});
  }, []);

  const operatorLabel = legal.legal_entity_incorporated
    ? legal.legal_entity_name
    : 'ChessMate (beta)';

  return (
    <LegalPage title="Terms of Service (Beta)">
      <p>
        ChessMate is in <strong>beta</strong>. By creating an account or using the service you agree to these terms
        and our <LegalLink to="/privacy">Privacy Policy</LegalLink>.
        We may change features, pricing, or availability during beta; material changes will be reflected on this page.
      </p>

      <h2 className="text-xl font-semibold mt-6 mb-2">Operator</h2>
      <p>
        The service is operated by <strong>{operatorLabel}</strong>
        {legal.legal_entity_address ? (
          <> ({legal.legal_entity_address})</>
        ) : null}
        . During beta, features and pricing may change; incorporated entity details will be updated on this page when finalized.
      </p>

      <h2 className="text-xl font-semibold mt-6 mb-2">The service</h2>
      <p>
        ChessMate imports chess games from platforms you connect (e.g. Chess.com, Lichess), runs Stockfish engine
        analysis, and may generate AI-assisted batch coaching reports. Analysis and coaching are automated
        estimates — not human coaching and not guaranteed to be complete or error-free.
      </p>

      <h2 className="text-xl font-semibold mt-6 mb-2">Accounts</h2>
      <ul className="list-disc pl-6 space-y-2">
        <li>You must provide accurate registration information and keep your credentials secure.</li>
        <li>You must be at least <strong>13 years old</strong> (or the minimum age required in your country) to use ChessMate.</li>
        <li>We may suspend or terminate accounts that violate these terms or pose a security risk.</li>
      </ul>

      <h2 className="text-xl font-semibold mt-6 mb-2">Credits & payments</h2>
      <ul className="list-disc pl-6 space-y-2">
        <li>
          Credits are sold as <strong>one-time packs</strong>, not subscriptions. Purchased credits do not expire
          while your account remains active unless stated otherwise at checkout.
        </li>
        <li>Importing a game typically costs <strong>1 credit</strong>. Batch Coach analysis is included once games are on your account.</li>
        <li>Payments are processed by Stripe. Refunds follow our refund policy and applicable law.</li>
      </ul>

      <h2 className="text-xl font-semibold mt-6 mb-2">Shared reports</h2>
      <p>
        You may generate a public link to a batch coaching report. Anyone with that link can view the shared content
        until you revoke sharing. You are responsible for who you share links with.
      </p>

      <h2 className="text-xl font-semibold mt-6 mb-2">Acceptable use</h2>
      <p>
        Do not abuse the API, scrape the service, attempt to access other users&apos; data, reverse-engineer protected
        parts of the product, or use ChessMate for unlawful purposes.
      </p>

      <h2 className="text-xl font-semibold mt-6 mb-2">Your content</h2>
      <p>
        You retain ownership of games and data you import. You grant ChessMate a limited license to store, process,
        analyze, and display that data to provide the service (including generating coaching text and shared reports).
      </p>

      <h2 className="text-xl font-semibold mt-6 mb-2">Governing law</h2>
      <p>
        These terms are governed by the laws of {legal.legal_governing_law}, without regard to conflict-of-law rules.
        If you are a consumer in a jurisdiction with mandatory local protections, those rights remain available to you
        where required by law.
      </p>

      <h2 className="text-xl font-semibold mt-6 mb-2">Disclaimer & liability</h2>
      <p>
        The service is provided <strong>&quot;as is&quot;</strong> during beta. To the maximum extent permitted by law,
        ChessMate is not liable for indirect or consequential damages, and our total liability is limited to amounts
        you paid us in the twelve months before the claim.
      </p>

      <h2 className="text-xl font-semibold mt-6 mb-2">Contact</h2>
      <p>
        Questions: <LegalLink href={`mailto:${legal.support_email}`}>{legal.support_email}</LegalLink>
      </p>
      <p className="text-sm opacity-75 mt-8">Last updated: June 2026</p>
    </LegalPage>
  );
};

export default TermsPage;
