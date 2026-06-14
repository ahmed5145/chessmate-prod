import React from 'react';
import LegalPage, { LegalLink } from './LegalPage';
import { useSiteConfig } from '../hooks/useSiteConfig';

const PrivacyPage = () => {
  const legal = useSiteConfig();

  const controllerLabel = legal.legal_entity_incorporated
    ? legal.legal_entity_name
    : 'ChessMate (beta operator)';

  return (
    <LegalPage title="Privacy Policy (Beta)">
      <p>
        ChessMate respects your privacy. This policy explains what we collect, why we use it, and your choices
        during the beta. It should be read together with our <LegalLink to="/terms">Terms of Service</LegalLink>.
      </p>

      <h2 className="text-xl font-semibold mt-6 mb-2">Data controller</h2>
      <p>
        <strong>{controllerLabel}</strong> is the data controller for personal information processed through ChessMate
        {legal.legal_entity_address ? (
          <> ({legal.legal_entity_address})</>
        ) : null}
        . When we incorporate, the registered entity name and address on this page will be updated.
      </p>

      <h2 className="text-xl font-semibold mt-6 mb-2">Information we collect</h2>
      <ul className="list-disc pl-6 space-y-2">
        <li><strong>Account data:</strong> email, username, password (stored hashed), and profile preferences.</li>
        <li><strong>Platform links:</strong> Chess.com and/or Lichess usernames you choose to connect for game import.</li>
        <li><strong>Game data:</strong> PGNs, results, dates, openings, engine analysis, and Batch Coach outputs.</li>
        <li><strong>Payment data:</strong> Stripe checkout metadata (we do not store full card numbers).</li>
        <li><strong>Technical data:</strong> session/authentication cookies, security logs, and basic usage needed to operate the service.</li>
      </ul>

      <h2 className="text-xl font-semibold mt-6 mb-2">How we use information</h2>
      <ul className="list-disc pl-6 space-y-2">
        <li>Authenticate you and operate credits, imports, and Batch Coach.</li>
        <li>Send transactional email (verification, password reset, batch completion when enabled).</li>
        <li>Generate coaching narratives from your analyzed game summaries.</li>
        <li>Maintain reliability, prevent abuse, and improve the product.</li>
      </ul>

      <h2 className="text-xl font-semibold mt-6 mb-2">Service providers</h2>
      <p>We use trusted processors to run ChessMate, including:</p>
      <ul className="list-disc pl-6 space-y-2">
        <li><strong>AWS</strong> — application hosting and data storage.</li>
        <li><strong>Stripe</strong> — payment processing.</li>
        <li><strong>OpenAI</strong> — generating Batch Coach narrative from structured game analysis (not your password).</li>
        <li><strong>Email delivery</strong> — transactional messages to your registered address.</li>
      </ul>
      <p>We do not sell your personal information.</p>

      <h2 className="text-xl font-semibold mt-6 mb-2">Shared batch reports</h2>
      <p>
        If you enable link sharing on a batch report, anyone with the URL can view that report without logging in
        until you revoke the link. Shared views may include game labels, analysis, and coaching text from that batch.
      </p>

      <h2 className="text-xl font-semibold mt-6 mb-2">Cookies & local storage</h2>
      <p>
        We use essential cookies for login sessions and CSRF protection. The app may store theme and UI preferences
        locally in your browser. We do not use third-party advertising cookies.
      </p>

      <h2 className="text-xl font-semibold mt-6 mb-2">Retention & deletion</h2>
      <p>
        We retain account and game data while your account is active. You may request account deletion by emailing us;
        we will delete or anonymize personal data within a reasonable period, subject to legal retention requirements.
      </p>

      <h2 className="text-xl font-semibold mt-6 mb-2">Your rights</h2>
      <p>
        Depending on where you live, you may have rights to access, correct, delete, or export personal data, or to
        object to certain processing. Contact us to exercise these rights. Disputes relating to privacy are handled under
        the governing law described in our <LegalLink to="/terms">Terms of Service</LegalLink> ({legal.legal_governing_law}),
        subject to mandatory consumer protections in your country.
      </p>

      <h2 className="text-xl font-semibold mt-6 mb-2">Children</h2>
      <p>
        ChessMate is not directed at children under 13. We do not knowingly collect data from children under 13.
      </p>

      <h2 className="text-xl font-semibold mt-6 mb-2">Contact</h2>
      <p>
        Privacy questions:{' '}
        {legal.support_email ? (
          <LegalLink href={`mailto:${legal.support_email}`}>{legal.support_email}</LegalLink>
        ) : (
          'contact support via the email shown in the site footer once loaded.'
        )}
      </p>
      <p className="text-sm opacity-75 mt-8">Last updated: June 2026</p>
    </LegalPage>
  );
};

export default PrivacyPage;
