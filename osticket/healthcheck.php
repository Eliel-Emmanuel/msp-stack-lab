<?php
// Healthcheck osTicket : Apache doit répondre en 2xx ou 3xx.
// On ne suit PAS les redirections : avec « Force HTTPS », osTicket renvoie un 302
// vers https://support.horizon.lan/, injoignable depuis l'intérieur du conteneur.
$contexte = stream_context_create(['http' => ['follow_location' => 0, 'timeout' => 4]]);
$entetes = @get_headers('http://127.0.0.1/', false, $contexte);

if ($entetes === false) {
    fwrite(STDERR, "Apache ne répond pas\n");
    exit(1);
}
if (!preg_match('#^HTTP/\S+ [23]\d\d#', $entetes[0])) {
    fwrite(STDERR, "Réponse inattendue : {$entetes[0]}\n");
    exit(1);
}
exit(0);
