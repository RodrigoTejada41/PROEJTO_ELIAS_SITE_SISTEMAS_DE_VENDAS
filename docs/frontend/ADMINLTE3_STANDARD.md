# AdminLTE 3

Requisito aprovado no pedido. Preferir a linha 3.2. Inventário inicial sem frontend ou dependências. Versão exata, dependências transitivas, licenças, suporte, segurança e combinação de CSS/JavaScript serão verificados antes da integração. Adotar apenas os plugins necessários. Exceções para AdminLTE 4, Bootstrap 5 ou outro template exigem aprovação explícita. Centralizar personalizações fora dos arquivos de terceiros.

## Integração HOM-001

CSS AdminLTE 3.2.0 obtido de admin-lte@3.2.0 do registro npm. O arquivo incorpora Bootstrap 4.6.1. Ambos usam licença MIT e suas licenças acompanham o CSS em app/static/vendor. A aplicação serve o CSS local, tema próprio e JavaScript nativo para o menu. Os plugins e scripts do pacote npm não fazem parte dos arquivos servidos. A instalação exploratória do pacote completo indicou dois alertas moderados. A versão embarcada permanece sujeita à revisão de segurança antes de publicação.
