import re

from django import forms
from PIL import Image

# App/company names are interpolated into single/double-quoted bash sed
# scripts in every generator workflow: & \ | corrupt the substitution
# silently, ' " $ ` break shell quoting, CR/LF break sed addressing.
UNSAFE_NAME_CHARS = re.compile(r'[&\\|\'"$`\r\n]')

class GenerateForm(forms.Form):
    sh_secret_field = forms.CharField(required=False)
    #Platform
    platform = forms.ChoiceField(choices=[('windows','Windows 64 bits'),('windows-x86','Windows 32 bits'),('linux','Linux'),('android','Android'),('macos','macOS')], initial='windows')
    version = forms.ChoiceField(choices=[('master','nightly'),('1.5.0','1.5.0'),('1.4.9','1.4.9'),('1.4.8','1.4.8'),('1.4.7','1.4.7'),('1.4.6','1.4.6'),('1.4.5','1.4.5'),('1.4.4','1.4.4'),('1.4.3','1.4.3'),('1.4.2','1.4.2'),('1.4.1','1.4.1'),('1.4.0','1.4.0')], initial='1.5.0')
    help_text="'master' é a versão de desenvolvimento (nightly), com as novidades, mas pode ser menos estável"
    delayFix = forms.BooleanField(initial=True, required=False)

    #General
    exename = forms.CharField(label="Nome da configuração", required=True)
    appname = forms.CharField(label="Nome do aplicativo", required=False)
    direction = forms.ChoiceField(widget=forms.RadioSelect, choices=[
        ('incoming', 'Somente entrada (só recebe acesso)'),
        ('outgoing', 'Somente saída (só acessa outros)'),
        ('both', 'Bidirecional')
    ], initial='both')
    installation = forms.ChoiceField(label="Desativar instalação", choices=[
        ('installationY', 'Não, permitir instalação'),
        ('installationN', 'Sim, DESATIVAR instalação')
    ], initial='installationY')
    settings = forms.ChoiceField(label="Desativar configurações", choices=[
        ('settingsY', 'Não, permitir configurações'),
        ('settingsN', 'Sim, DESATIVAR configurações')
    ], initial='settingsY')
    androidappid = forms.CharField(label="ID do app Android", required=False)

    #Custom Server
    serverIP = forms.CharField(label="Host", required=False)
    serverPort = forms.CharField(label="Porta", required=False)
    apiServer = forms.CharField(label="Servidor de API", required=False)
    key = forms.CharField(label="Chave", required=False)
    urlLink = forms.CharField(label="URL dos links", required=False)
    downloadLink = forms.CharField(label="URL para baixar atualizações", required=False)
    compname = forms.CharField(label="Nome da empresa",required=False)

    #Visual
    iconfile = forms.FileField(label="Ícone do aplicativo (PNG)", required=False, widget=forms.FileInput(attrs={'accept': 'image/png'}))
    logofile = forms.FileField(label="Logo do aplicativo (PNG)", required=False, widget=forms.FileInput(attrs={'accept': 'image/png'}))
    privacyfile = forms.FileField(label="Tela de privacidade (PNG)", required=False, widget=forms.FileInput(attrs={'accept': 'image/png'}))
    iconbase64 = forms.CharField(required=False)
    logobase64 = forms.CharField(required=False)
    privacybase64 = forms.CharField(required=False)
    theme = forms.ChoiceField(choices=[
        ('light', 'Claro'),
        ('dark', 'Escuro'),
        ('system', 'Seguir o sistema')
    ], initial='system')
    themeDorO = forms.ChoiceField(choices=[('default', 'Padrão'),('override', 'Fixo')], initial='default')

    #Security
    passApproveMode = forms.ChoiceField(choices=[('password','Aceitar sessões por senha'),('click','Aceitar sessões por clique'),('password-click','Aceitar sessões por senha e clique')],initial='password-click')
    permanentPassword = forms.CharField(widget=forms.PasswordInput(), required=False)
    #runasadmin = forms.ChoiceField(choices=[('false','No'),('true','Yes')], initial='false')
    denyLan = forms.BooleanField(initial=False, required=False)
    enableDirectIP = forms.BooleanField(initial=False, required=False)
    #ipWhitelist = forms.BooleanField(initial=False, required=False)
    autoClose = forms.BooleanField(initial=False, required=False)

    #Permissions
    permissionsDorO = forms.ChoiceField(choices=[('default', 'Padrão (usuário pode alterar)'),('override', 'Fixas (não podem ser alteradas)')], initial='default')
    permissionsType = forms.ChoiceField(choices=[('custom', 'Personalizado'),('full', 'Acesso total'),('view','Somente visualização')], initial='custom')
    enableKeyboard =  forms.BooleanField(initial=True, required=False)
    enableClipboard = forms.BooleanField(initial=True, required=False)
    enableFileTransfer = forms.BooleanField(initial=True, required=False)
    enableAudio = forms.BooleanField(initial=True, required=False)
    enableTCP = forms.BooleanField(initial=True, required=False)
    enableRemoteRestart = forms.BooleanField(initial=True, required=False)
    enableRecording = forms.BooleanField(initial=True, required=False)
    enableBlockingInput = forms.BooleanField(initial=True, required=False)
    enableRemoteModi = forms.BooleanField(initial=False, required=False)
    hidecm = forms.BooleanField(initial=False, required=False)
    enablePrinter = forms.BooleanField(initial=True, required=False)
    enableCamera = forms.BooleanField(initial=True, required=False)
    enableTerminal = forms.BooleanField(initial=True, required=False)

    #Other
    removeWallpaper = forms.BooleanField(initial=True, required=False)

    defaultManual = forms.CharField(widget=forms.Textarea, required=False)
    overrideManual = forms.CharField(widget=forms.Textarea, required=False)

    #custom added features
    xOffline = forms.BooleanField(initial=False, required=False)
    removeNewVersionNotif = forms.BooleanField(initial=False, required=False)

    def clean_iconfile(self):
        print("checking icon")
        image = self.cleaned_data['iconfile']
        if image:
            try:
                # Open the image using Pillow
                img = Image.open(image)

                # Check if the image is a PNG (optional, but good practice)
                if img.format != 'PNG':
                    raise forms.ValidationError("Apenas imagens PNG são permitidas.")

                # Get image dimensions
                width, height = img.size

                # Check for square dimensions
                if width != height:
                    raise forms.ValidationError("O ícone do aplicativo precisa ser quadrado.")
                
                return image
            except OSError:  # Handle cases where the uploaded file is not a valid image
                raise forms.ValidationError("Arquivo de ícone inválido.")
            except Exception as e: # Catch any other image processing errors
                raise forms.ValidationError(f"Erro ao processar o ícone: {e}")

    def _reject_unsafe_name_chars(self, field):
        value = self.cleaned_data.get(field, '')
        if value and UNSAFE_NAME_CHARS.search(value):
            raise forms.ValidationError(
                "Contém caracteres não suportados pelos scripts de compilação "
                "(& \\ | ' \" $ `, quebras de linha)."
            )
        return value

    def clean_appname(self):
        return self._reject_unsafe_name_chars('appname')

    def clean_compname(self):
        return self._reject_unsafe_name_chars('compname')
