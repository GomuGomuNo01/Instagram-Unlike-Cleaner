import { Demo } from './home/Demo'
import { Hero } from './home/Hero'
import { HowItWorks } from './home/HowItWorks'
import { Benefits, Commitments, Faq, Features, FinalCallToAction, Security } from './home/Sections'

/** Page d'accueil. Chaque section a un objectif : convaincre (héros, engagements,
 * avantages), expliquer (fonctionnement, fonctionnalités), faire essayer (démonstration),
 * rassurer (sécurité, FAQ), puis inviter à commencer. Pas de témoignages : IUC n'en invente
 * pas, les engagements vérifiables en tiennent lieu. */
export function HomePage() {
  return (
    <>
      <Hero />
      <Commitments />
      <Benefits />
      <HowItWorks />
      <Features />
      <Demo />
      <Security />
      <Faq />
      <FinalCallToAction />
    </>
  )
}
