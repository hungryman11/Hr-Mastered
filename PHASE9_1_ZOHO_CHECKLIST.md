# Zoho UAT Preparation Checklist

Never commit real credentials or use production secrets in development/UAT.

| Item | Developer environment | Infinity UAT environment | Production environment |
|---|---|---|---|
| OAuth client ID/secret | Developer-owned test app | Infinity-approved UAT app | Infinity-approved production app |
| Redirect URIs | Local callback only | UAT platform callback approved in Zoho | Production HTTPS callback approved in Zoho |
| Scopes | Minimum required configured scopes | Confirm same/minimum scopes with Infinity admin | Formal least-privilege approval |
| Zoho People | Mock/test availability | Confirm tenant access and test employee behavior | Confirm support/ownership |
| Zoho Mail | Mock/test sender | Approved test sender/account | Approved monitored production sender |
| Zoho WorkDrive | Test folder/account | UAT folder and permission model | Production retention/access policy |
| Accounts | Synthetic developer accounts | Named HR test accounts | Named operational/admin accounts |
| Organisation data | Non-production | Infinity UAT organisation/account information | Production organisation/account information |

Infinity must supply/approve: OAuth credentials through a secure channel, each redirect URI, required scopes, Zoho organisation identifiers, test accounts, People/Mail/WorkDrive availability and an authorised Zoho administrator. Validate callback, token refresh, failed-token handling and document/email delivery in UAT before production sign-off.
