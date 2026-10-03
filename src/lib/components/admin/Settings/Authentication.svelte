<script lang="ts">
	import { getBackendConfig } from '$lib/apis';
	import {
		getAdminConfig,
		getLdapConfig,
		getLdapServer,
		getOAuthConfig,
		updateLdapConfig,
		updateLdapServer,
		updateOAuthConfig,
		updateAdminConfig
	} from '$lib/apis/auths';
	import { getGroups } from '$lib/apis/groups';
	import SensitiveInput from '$lib/components/common/SensitiveInput.svelte';
	import Switch from '$lib/components/common/Switch.svelte';
	import Textarea from '$lib/components/common/Textarea.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import { config } from '$lib/stores';
	import { getContext, onMount, tick } from 'svelte';
	import { toast } from 'svelte-sonner';
	import { v4 as uuidv4 } from 'uuid';
	import AdminSettingField from './AdminSettingField.svelte';
	import AdminSettingRow from './AdminSettingRow.svelte';
	import AdminSettingSection from './AdminSettingSection.svelte';
	import SettingsSelect from '$lib/components/common/SettingsSelect.svelte';
	import Modal from '$lib/components/common/Modal.svelte';
	import Plus from '$lib/components/icons/Plus.svelte';
	import XMark from '$lib/components/icons/XMark.svelte';

	const i18n: any = getContext('i18n');

	let adminConfig: any = null;
	let groups: any[] = [];

	let ENABLE_LDAP = false;
	let LDAP_SERVER = {
		label: '',
		host: '',
		port: null,
		attribute_for_mail: 'mail',
		attribute_for_username: 'uid',
		app_dn: '',
		app_dn_password: '',
		search_base: '',
		search_filters: '',
		use_tls: false,
		validate_cert: false,
		certificate_path: '',
		ciphers: '',
		enable_group_management: false,
		enable_group_creation: false,
		attribute_for_groups: 'memberOf'
	};

	let oauthConfig: any = null;
	$: oauthEditable = oauthConfig?.ENABLE_OAUTH_PERSISTENT_CONFIG ?? true;
	const inputClass =
		'w-full h-7 rounded-lg border border-gray-100/50 bg-gray-50/40 px-2 text-xs text-gray-700 outline-hidden transition-colors placeholder:text-gray-300 focus:border-blue-400 dark:border-white/[0.04] dark:bg-white/[0.03] dark:text-gray-300 dark:placeholder:text-gray-700 dark:focus:border-blue-500';
	const textareaClass =
		'w-full rounded-lg border border-gray-100/50 bg-gray-50/40 px-2 py-1.5 text-xs text-gray-700 outline-hidden transition-colors placeholder:text-gray-300 focus:border-blue-400 dark:border-white/[0.04] dark:bg-white/[0.03] dark:text-gray-300 dark:placeholder:text-gray-700 dark:focus:border-blue-500';

	const updateLdapServerHandler = async () => {
		await updateLdapConfig(localStorage.token, ENABLE_LDAP);
		if (!ENABLE_LDAP) return true;

		// Honor the "Default to memberOf" hint: fall back to the default group
		// attribute when it is left blank while group management is enabled, so
		// the save isn't rejected by the backend's required-field check.
		if (LDAP_SERVER.enable_group_management && !LDAP_SERVER.attribute_for_groups?.trim()) {
			LDAP_SERVER.attribute_for_groups = 'memberOf';
		}

		const res = await updateLdapServer(localStorage.token, LDAP_SERVER).catch((error) => {
			toast.error(`${error}`);
			return null;
		});

		return !!res;
	};

	const updateOAuthHandler = async () => {
		if (!oauthConfig || !oauthEditable) return true;
		const res = await updateOAuthConfig(localStorage.token, oauthConfig).catch((error) => {
			toast.error(`${error}`);
			return null;
		});
		if (res) {
			oauthConfig = res;
		}
		return !!res;
	};

	let showPickerUserModal = false;
	let pickerUserDraft = { _key: '', name: '', email: '', profile_image_url: '' };

	const blankPickerUser = () => ({
		_key: uuidv4(),
		name: '',
		email: '',
		profile_image_url: ''
	});

	const openAddPickerUser = () => {
		pickerUserDraft = blankPickerUser();
		showPickerUserModal = true;
	};

	const openEditPickerUser = (pickerUser) => {
		pickerUserDraft = {
			_key: pickerUser._key,
			name: pickerUser.name ?? '',
			email: pickerUser.email ?? '',
			profile_image_url: pickerUser.profile_image_url ?? ''
		};
		showPickerUserModal = true;
	};

	const setPickerUsers = (users) => {
		adminConfig = { ...adminConfig, USER_PICKER_USERS: users };
	};

	// True when saving would leave the login page with no password form, no picker
	// accounts, and no SSO, LDAP, or trusted-header sign-in.
	const signInWouldBeLockedOut = ({
		loginForm = adminConfig?.ENABLE_LOGIN_FORM,
		pickerEnabled = adminConfig?.ENABLE_USER_PICKER_LOGIN,
		pickerUsers = adminConfig?.USER_PICKER_USERS
	} = {}) => {
		if ($config?.features?.auth === false || $config?.features?.auth_trusted_header) return false;
		if (loginForm) return false;
		const ready = (pickerUsers ?? []).filter(
			(pickerUser) => `${pickerUser?.name ?? ''}`.trim() && `${pickerUser?.email ?? ''}`.trim()
		);
		if (pickerEnabled && ready.length > 0) return false;
		if (ENABLE_LDAP || oauthConfig?.ENABLE_OAUTH) return false;
		return true;
	};

	const lockoutMessage = () =>
		$i18n.t(
			'Leave the login form on until User Picker Login has at least one person, or turn on SSO or LDAP first.'
		);

	const removePickerUser = (index) => {
		const next = adminConfig.USER_PICKER_USERS.filter((_, idx) => idx !== index);
		if (signInWouldBeLockedOut({ pickerUsers: next })) {
			toast.error(lockoutMessage());
			return;
		}
		setPickerUsers(next);
	};

	const savePickerUserDraft = () => {
		const name = pickerUserDraft.name.trim();
		const email = pickerUserDraft.email.trim();
		const profileImageUrl = pickerUserDraft.profile_image_url.trim();
		if (!name || !email) {
			toast.error($i18n.t('Each user picker entry needs a display name and email.'));
			return;
		}

		const others = (adminConfig.USER_PICKER_USERS ?? []).filter(
			(pickerUser) => pickerUser._key !== pickerUserDraft._key
		);
		if (others.some((pickerUser) => pickerUser.email.trim().toLowerCase() === email.toLowerCase())) {
			toast.error($i18n.t('User picker emails must be unique.'));
			return;
		}

		const nextUser = {
			_key: pickerUserDraft._key || uuidv4(),
			name,
			email,
			profile_image_url: profileImageUrl
		};
		const exists = (adminConfig.USER_PICKER_USERS ?? []).some(
			(pickerUser) => pickerUser._key === nextUser._key
		);
		setPickerUsers(
			exists
				? adminConfig.USER_PICKER_USERS.map((pickerUser) =>
						pickerUser._key === nextUser._key ? nextUser : pickerUser
					)
				: [...(adminConfig.USER_PICKER_USERS ?? []), nextUser]
		);
		showPickerUserModal = false;
	};

	// Blank rows are dropped. Incomplete rows are rejected before save so the
	// explicit picker list stays limited to name, email, and an optional avatar.
	const pickerUsersForSave = () => {
		const users = (adminConfig.USER_PICKER_USERS ?? [])
			.map((pickerUser) => ({
				name: `${pickerUser?.name ?? ''}`.trim(),
				email: `${pickerUser?.email ?? ''}`.trim(),
				profile_image_url: `${pickerUser?.profile_image_url ?? ''}`.trim()
			}))
			.filter((pickerUser) => pickerUser.name || pickerUser.email || pickerUser.profile_image_url);

		if (users.some((pickerUser) => !pickerUser.name || !pickerUser.email)) {
			toast.error($i18n.t('Each user picker entry needs a display name and email.'));
			return null;
		}

		const emails = users.map((pickerUser) => pickerUser.email.toLowerCase());
		if (new Set(emails).size !== emails.length) {
			toast.error($i18n.t('User picker emails must be unique.'));
			return null;
		}

		return users;
	};

	const updateAdminHandler = async () => {
		if (!adminConfig) return true;
		const pickerUsers = pickerUsersForSave();
		if (!pickerUsers) return false;
		if (signInWouldBeLockedOut({ pickerUsers })) {
			toast.error(lockoutMessage());
			return false;
		}
		adminConfig.USER_PICKER_USERS = pickerUsers;
		const res = await updateAdminConfig(localStorage.token, adminConfig).catch((error) => {
			toast.error(`${error}`);
			return null;
		});
		return !!res;
	};

	const submitHandler = async () => {
		if (adminConfig && signInWouldBeLockedOut()) {
			toast.error(lockoutMessage());
			return;
		}
		// Save SSO and LDAP first so the login-form check can see them.
		const ldapSaved = await updateLdapServerHandler();
		const oauthSaved = await updateOAuthHandler();
		const adminSaved = await updateAdminHandler();

		if (adminSaved && ldapSaved && oauthSaved) {
			toast.success($i18n.t('Settings saved successfully!'));
			await config.set(await getBackendConfig());
		}
	};

	onMount(async () => {
		await Promise.all([
			(async () => {
				adminConfig = await getAdminConfig(localStorage.token);
				adminConfig.ENABLE_USER_PICKER_LOGIN = !!adminConfig.ENABLE_USER_PICKER_LOGIN;
				adminConfig.USER_PICKER_USERS = Array.isArray(adminConfig.USER_PICKER_USERS)
					? adminConfig.USER_PICKER_USERS.map((pickerUser) => ({
							_key: uuidv4(),
							name: pickerUser?.name ?? '',
							email: pickerUser?.email ?? '',
							profile_image_url: pickerUser?.profile_image_url ?? ''
						}))
					: [];
			})(),
			(async () => {
				groups = await getGroups(localStorage.token);
			})(),
			(async () => {
				// Merge into the defaults so any key the backend omits (e.g. an
				// older backend without the group settings) keeps its default.
				LDAP_SERVER = { ...LDAP_SERVER, ...(await getLdapServer(localStorage.token)) };
			})(),
			(async () => {
				oauthConfig = await getOAuthConfig(localStorage.token).catch(() => null);
			})()
		]);

		const ldapConfig = await getLdapConfig(localStorage.token);
		ENABLE_LDAP = ldapConfig.ENABLE_LDAP;
	});
</script>

<form class="flex h-full flex-col justify-between text-sm" on:submit|preventDefault={submitHandler}>
	<h2 class="text-sm font-medium text-gray-900 dark:text-white mb-4">
		{$i18n.t('settings.admin.authentication.title')}
	</h2>

	<div class="flex-1 min-h-0 overflow-y-auto scrollbar-hover pr-1.5">
		{#if adminConfig !== null}
			<AdminSettingSection
				title={$i18n.t('settings.admin.authentication.sections.userAccess.title')}
				first
			>
				<AdminSettingRow
					label={$i18n.t('settings.admin.authentication.defaultUserRole.label')}
					description={$i18n.t('settings.admin.authentication.defaultUserRole.description')}
				>
					<SettingsSelect
						bind:value={adminConfig.DEFAULT_USER_ROLE}
						placeholder={$i18n.t('Select a role')}
					>
						<option value="pending">{$i18n.t('pending')}</option>
						<option value="user">{$i18n.t('user')}</option>
						<option value="admin">{$i18n.t('admin')}</option>
					</SettingsSelect>
				</AdminSettingRow>

				<AdminSettingRow
					label={$i18n.t('settings.admin.authentication.defaultGroup.label')}
					description={$i18n.t('settings.admin.authentication.defaultGroup.description')}
				>
					<SettingsSelect
						bind:value={adminConfig.DEFAULT_GROUP_ID}
						placeholder={$i18n.t('Select a group')}
					>
						<option value={''}>{$i18n.t('None')}</option>
						{#each groups as group}
							<option value={group.id}>{group.name}</option>
						{/each}
					</SettingsSelect>
				</AdminSettingRow>

				<AdminSettingRow
					label={$i18n.t('settings.admin.authentication.loginForm.label')}
					description={$i18n.t('settings.admin.authentication.loginForm.description')}
					let:labelId
				>
					<Switch
						bind:state={adminConfig.ENABLE_LOGIN_FORM}
						ariaLabelledbyId={labelId}
						on:change={async (event) => {
							if (event.detail === false && signInWouldBeLockedOut()) {
								await tick();
								adminConfig.ENABLE_LOGIN_FORM = true;
								toast.error(lockoutMessage());
							}
						}}
					/>
				</AdminSettingRow>

				<AdminSettingRow
					label={$i18n.t('settings.admin.authentication.userPicker.label')}
					description={$i18n.t('settings.admin.authentication.userPicker.description')}
					let:labelId
				>
					<Switch
						bind:state={adminConfig.ENABLE_USER_PICKER_LOGIN}
						ariaLabelledbyId={labelId}
						on:change={async (event) => {
							if (event.detail === false && signInWouldBeLockedOut()) {
								await tick();
								adminConfig.ENABLE_USER_PICKER_LOGIN = true;
								toast.error(lockoutMessage());
							}
						}}
					/>
				</AdminSettingRow>

				{#if adminConfig.ENABLE_USER_PICKER_LOGIN}
					<div>
						<div class="mb-1 flex min-h-7 items-center justify-between gap-2">
							<div class="min-w-0 text-xs text-gray-600 dark:text-gray-400">
								{$i18n.t('settings.admin.authentication.userPickerUsers.label')}
							</div>
							<button
								class="flex size-6 cursor-pointer items-center justify-center text-gray-400 hover:text-gray-700 dark:text-gray-600 dark:hover:text-gray-300"
								type="button"
								aria-label={$i18n.t('settings.admin.authentication.userPickerAdd.label')}
								on:click|stopPropagation={openAddPickerUser}
							>
								<Plus className="size-4" />
							</button>
						</div>
						<p class="mb-2 text-[0.6875rem] text-gray-400 dark:text-gray-600">
							{$i18n.t('settings.admin.authentication.userPickerUsers.description')}
						</p>
						{#if adminConfig.USER_PICKER_USERS.length === 0}
							<p class="text-[0.6875rem] text-gray-400 dark:text-gray-600">
								{$i18n.t('No accounts yet. Use + to add someone to the login page.')}
							</p>
						{/if}
						<div class="flex flex-col gap-1.5">
							{#each adminConfig.USER_PICKER_USERS as pickerUser, pickerUserIdx (pickerUser._key)}
								<div
									class="flex items-center gap-2 rounded-lg border border-gray-100/40 px-2 py-1.5 dark:border-gray-850/50"
								>
									<button
										class="min-w-0 flex-1 text-left"
										type="button"
										on:click={() => openEditPickerUser(pickerUser)}
									>
										<div class="truncate text-xs text-gray-700 dark:text-gray-200">
											{pickerUser.name}
										</div>
										<div class="truncate text-[0.6875rem] text-gray-400 dark:text-gray-500">
											{pickerUser.email}
										</div>
									</button>
									<button
										class="flex size-6 shrink-0 items-center justify-center text-gray-400 hover:text-gray-700 dark:text-gray-600 dark:hover:text-gray-300"
										type="button"
										aria-label={$i18n.t('Delete')}
										on:click={() => removePickerUser(pickerUserIdx)}
									>
										<XMark className="size-3.5" />
									</button>
								</div>
							{/each}
						</div>
					</div>
				{/if}

				<AdminSettingRow
					label={$i18n.t('settings.admin.authentication.newSignUps.label')}
					description={$i18n.t('settings.admin.authentication.newSignUps.description')}
					let:labelId
				>
					<Switch bind:state={adminConfig.ENABLE_SIGNUP} ariaLabelledbyId={labelId} />
				</AdminSettingRow>

				<AdminSettingRow
					label={$i18n.t('settings.admin.authentication.apiKeys.label')}
					description={$i18n.t('settings.admin.authentication.apiKeys.description')}
					let:labelId
				>
					<Switch bind:state={adminConfig.ENABLE_API_KEYS} ariaLabelledbyId={labelId} />
				</AdminSettingRow>

				{#if adminConfig?.ENABLE_API_KEYS}
					<AdminSettingRow
						label={$i18n.t('settings.admin.authentication.apiKeyEndpointRestrictions.label')}
						description={$i18n.t(
							'settings.admin.authentication.apiKeyEndpointRestrictions.description'
						)}
						let:labelId
					>
						<Switch
							bind:state={adminConfig.ENABLE_API_KEYS_ENDPOINT_RESTRICTIONS}
							ariaLabelledbyId={labelId}
						/>
					</AdminSettingRow>

					{#if adminConfig?.ENABLE_API_KEYS_ENDPOINT_RESTRICTIONS}
						<AdminSettingField
							label={$i18n.t('settings.admin.authentication.allowedEndpoints.label')}
							description={$i18n.t('settings.admin.authentication.allowedEndpoints.description')}
						>
							<input
								class={inputClass}
								type="text"
								placeholder={`e.g.) /api/v1/messages, /api/v1/channels`}
								bind:value={adminConfig.API_KEYS_ALLOWED_ENDPOINTS}
							/>
							<a
								href="https://docs.openwebui.com/reference/api-endpoints"
								target="_blank"
								class="mt-1 block text-[0.6875rem] text-gray-400 underline hover:text-gray-700 dark:text-gray-600 dark:hover:text-gray-300"
							>
								{$i18n.t('To learn more about available endpoints, visit our documentation.')}
							</a>
						</AdminSettingField>
					{/if}
				{/if}

				<AdminSettingField
					label={$i18n.t('settings.admin.authentication.jwtExpiration.label')}
					description={$i18n.t('settings.admin.authentication.jwtExpiration.description')}
				>
					<input
						class={inputClass}
						type="text"
						placeholder={`e.g.) "30m","1h", "10d". `}
						bind:value={adminConfig.JWT_EXPIRES_IN}
					/>

					{#if adminConfig.JWT_EXPIRES_IN === '-1'}
						<a
							href="https://docs.openwebui.com/reference/env-configuration#jwt_expires_in"
							target="_blank"
							class="mt-1 block rounded-lg bg-yellow-500/10 px-2 py-1.5 text-[0.6875rem] text-yellow-700 underline dark:text-yellow-200"
						>
							{$i18n.t('No expiration can pose security risks.')}
						</a>
					{/if}
				</AdminSettingField>
			</AdminSettingSection>

			<AdminSettingSection
				title={$i18n.t('settings.admin.authentication.sections.pendingAccounts.title')}
			>
				<AdminSettingRow
					label={$i18n.t('settings.admin.authentication.adminDetails.label')}
					description={$i18n.t('settings.admin.authentication.adminDetails.description')}
					let:labelId
				>
					<Switch bind:state={adminConfig.SHOW_ADMIN_DETAILS} ariaLabelledbyId={labelId} />
				</AdminSettingRow>

				{#if adminConfig.SHOW_ADMIN_DETAILS}
					<AdminSettingField
						label={$i18n.t('settings.admin.authentication.adminContactEmail.label')}
						description={$i18n.t('settings.admin.authentication.adminContactEmail.description')}
					>
						<input
							class={inputClass}
							type="email"
							placeholder={$i18n.t('Leave empty to use first admin user')}
							bind:value={adminConfig.ADMIN_EMAIL}
						/>
					</AdminSettingField>
				{/if}

				<AdminSettingField
					label={$i18n.t('settings.admin.authentication.pendingUserOverlayTitle.label')}
					description={$i18n.t('settings.admin.authentication.pendingUserOverlayTitle.description')}
				>
					<Textarea
						className={textareaClass}
						placeholder={$i18n.t(
							'Enter a title for the pending user info overlay. Leave empty for default.'
						)}
						bind:value={adminConfig.PENDING_USER_OVERLAY_TITLE}
					/>
				</AdminSettingField>

				<AdminSettingField
					label={$i18n.t('settings.admin.authentication.pendingUserOverlayContent.label')}
					description={$i18n.t(
						'settings.admin.authentication.pendingUserOverlayContent.description'
					)}
				>
					<Textarea
						className={textareaClass}
						placeholder={$i18n.t(
							'Enter content for the pending user info overlay. Leave empty for default.'
						)}
						bind:value={adminConfig.PENDING_USER_OVERLAY_CONTENT}
					/>
				</AdminSettingField>
			</AdminSettingSection>
		{/if}

		<AdminSettingSection title={$i18n.t('settings.admin.authentication.sections.ldap.title')}>
			<AdminSettingRow
				label={$i18n.t('settings.admin.authentication.ldap.label')}
				description={$i18n.t('settings.admin.authentication.ldap.description')}
				let:labelId
			>
				<Switch bind:state={ENABLE_LDAP} ariaLabelledbyId={labelId} />
			</AdminSettingRow>

			{#if ENABLE_LDAP}
				<div class="grid grid-cols-1 gap-x-3 gap-y-2.5 sm:grid-cols-2">
					<AdminSettingField
						label={$i18n.t('settings.admin.authentication.label.label')}
						description={$i18n.t('settings.admin.authentication.label.description')}
					>
						<input
							class={inputClass}
							required
							placeholder={$i18n.t('Enter server label')}
							bind:value={LDAP_SERVER.label}
						/>
					</AdminSettingField>
				</div>

				<div class="grid grid-cols-1 gap-x-3 gap-y-2.5 sm:grid-cols-2">
					<AdminSettingField
						label={$i18n.t('settings.admin.authentication.host.label')}
						description={$i18n.t('settings.admin.authentication.host.description')}
					>
						<input
							class={inputClass}
							required
							placeholder={$i18n.t('Enter server host')}
							bind:value={LDAP_SERVER.host}
						/>
					</AdminSettingField>

					<AdminSettingField
						label={$i18n.t('settings.admin.authentication.port.label')}
						description={$i18n.t('settings.admin.authentication.port.description')}
					>
						<Tooltip
							placement="top-start"
							content={$i18n.t('Default to 389 or 636 if TLS is enabled')}
							className="w-full"
						>
							<input
								class={inputClass}
								type="number"
								placeholder={$i18n.t('Enter server port')}
								bind:value={LDAP_SERVER.port}
							/>
						</Tooltip>
					</AdminSettingField>
				</div>

				<div class="grid grid-cols-1 gap-x-3 gap-y-2.5 sm:grid-cols-2">
					<AdminSettingField
						label={$i18n.t('settings.admin.authentication.applicationDn.label')}
						description={$i18n.t('settings.admin.authentication.applicationDn.description')}
					>
						<Tooltip
							content={$i18n.t('The Application Account DN you bind with for search')}
							placement="top-start"
						>
							<input
								class={inputClass}
								placeholder={$i18n.t('Enter Application DN')}
								bind:value={LDAP_SERVER.app_dn}
							/>
						</Tooltip>
					</AdminSettingField>

					<AdminSettingField
						label={$i18n.t('settings.admin.authentication.applicationDnPassword.label')}
						description={$i18n.t('settings.admin.authentication.applicationDnPassword.description')}
					>
						<SensitiveInput
							variant="settings"
							placeholder={$i18n.t('Enter Application DN Password')}
							required={false}
							bind:value={LDAP_SERVER.app_dn_password}
						/>
					</AdminSettingField>
				</div>

				<div class="grid grid-cols-1 gap-x-3 gap-y-2.5 sm:grid-cols-2">
					<AdminSettingField
						label={$i18n.t('settings.admin.authentication.attributeForMail.label')}
						description={$i18n.t('settings.admin.authentication.attributeForMail.description')}
					>
						<Tooltip
							content={$i18n.t(
								'The LDAP attribute that maps to the mail that users use to sign in.'
							)}
							placement="top-start"
						>
							<input
								class={inputClass}
								required
								placeholder={$i18n.t('Example: mail')}
								bind:value={LDAP_SERVER.attribute_for_mail}
							/>
						</Tooltip>
					</AdminSettingField>

					<AdminSettingField
						label={$i18n.t('settings.admin.authentication.attributeForUsername.label')}
						description={$i18n.t('settings.admin.authentication.attributeForUsername.description')}
					>
						<Tooltip
							content={$i18n.t(
								'The LDAP attribute that maps to the username that users use to sign in.'
							)}
							placement="top-start"
						>
							<input
								class={inputClass}
								required
								placeholder={$i18n.t('Example: sAMAccountName or uid or userPrincipalName')}
								bind:value={LDAP_SERVER.attribute_for_username}
							/>
						</Tooltip>
					</AdminSettingField>
				</div>

				<AdminSettingField
					label={$i18n.t('settings.admin.authentication.searchBase.label')}
					description={$i18n.t('settings.admin.authentication.searchBase.description')}
				>
					<Tooltip content={$i18n.t('The base to search for users')} placement="top-start">
						<input
							class={inputClass}
							required
							placeholder={$i18n.t('Example: ou=users,dc=foo,dc=example')}
							bind:value={LDAP_SERVER.search_base}
						/>
					</Tooltip>
				</AdminSettingField>

				<AdminSettingField
					label={$i18n.t('settings.admin.authentication.searchFilters.label')}
					description={$i18n.t('settings.admin.authentication.searchFilters.description')}
				>
					<input
						class={inputClass}
						placeholder={$i18n.t('Example: (&(objectClass=inetOrgPerson)(uid=%s))')}
						bind:value={LDAP_SERVER.search_filters}
					/>
					<a
						class="mt-1 block text-[0.6875rem] text-gray-400 underline hover:text-gray-700 dark:text-gray-600 dark:hover:text-gray-300"
						href="https://ldap.com/ldap-filters/"
						target="_blank"
					>
						{$i18n.t('Click here for filter guides.')}
					</a>
				</AdminSettingField>

				<AdminSettingRow
					label={$i18n.t('settings.admin.authentication.tls.label')}
					description={$i18n.t('settings.admin.authentication.tls.description')}
					let:labelId
				>
					<Switch bind:state={LDAP_SERVER.use_tls} ariaLabelledbyId={labelId} />
				</AdminSettingRow>

				{#if LDAP_SERVER.use_tls}
					<AdminSettingField
						label={$i18n.t('settings.admin.authentication.certificatePath.label')}
						description={$i18n.t('settings.admin.authentication.certificatePath.description')}
					>
						<input
							class={inputClass}
							placeholder={$i18n.t('Enter certificate path')}
							bind:value={LDAP_SERVER.certificate_path}
						/>
					</AdminSettingField>

					<AdminSettingRow
						label={$i18n.t('settings.admin.authentication.validateCertificate.label')}
						description={$i18n.t('settings.admin.authentication.validateCertificate.description')}
						let:labelId
					>
						<Switch bind:state={LDAP_SERVER.validate_cert} ariaLabelledbyId={labelId} />
					</AdminSettingRow>

					<AdminSettingField
						label={$i18n.t('settings.admin.authentication.ciphers.label')}
						description={$i18n.t('settings.admin.authentication.ciphers.description')}
					>
						<Tooltip content={$i18n.t('Default to ALL')} placement="top-start">
							<input
								class={inputClass}
								placeholder={$i18n.t('Example: ALL')}
								bind:value={LDAP_SERVER.ciphers}
							/>
						</Tooltip>
					</AdminSettingField>
				{/if}

				<!-- LICENSE covers this Open WebUI wordmark.
					Do not alter, remove, obscure, or replace it except as LICENSE permits:
					https://docs.openwebui.com/license. -->
				<AdminSettingRow
					label={$i18n.t('settings.admin.authentication.enableGroupManagement.label')}
					description={$i18n.t('settings.admin.authentication.enableGroupManagement.description')}
					let:labelId
				>
					<Switch bind:state={LDAP_SERVER.enable_group_management} ariaLabelledbyId={labelId} />
				</AdminSettingRow>

				{#if LDAP_SERVER.enable_group_management}
					<AdminSettingRow
						label={$i18n.t('settings.admin.authentication.enableGroupCreation.label')}
						description={$i18n.t('settings.admin.authentication.enableGroupCreation.description')}
						let:labelId
					>
						<Switch bind:state={LDAP_SERVER.enable_group_creation} ariaLabelledbyId={labelId} />
					</AdminSettingRow>

					<AdminSettingField
						label={$i18n.t('settings.admin.authentication.groupAttribute.label')}
						description={$i18n.t('settings.admin.authentication.groupAttribute.description')}
					>
						<Tooltip content={$i18n.t('Default to memberOf')} placement="top-start">
							<input
								class={inputClass}
								placeholder="memberOf"
								bind:value={LDAP_SERVER.attribute_for_groups}
							/>
						</Tooltip>
					</AdminSettingField>
				{/if}
			{/if}
		</AdminSettingSection>

		{#if oauthConfig}
			<AdminSettingSection
				title={$i18n.t('settings.admin.authentication.sections.oauthOidc.title')}
			>
				{#if !oauthEditable}
					<div
						class="rounded-lg bg-yellow-500/10 px-2 py-1.5 text-[0.6875rem] text-yellow-700 dark:text-yellow-200"
					>
						{$i18n.t(
							'These settings are read from environment variables and cannot be edited here while {{ENV_VAR}} is disabled.',
							{ ENV_VAR: 'ENABLE_OAUTH_PERSISTENT_CONFIG' }
						)}
					</div>
				{/if}

				<fieldset
					class="flex min-w-0 flex-col gap-2.5 disabled:cursor-not-allowed disabled:opacity-75"
					disabled={!oauthEditable}
				>
					<AdminSettingRow
						label={$i18n.t('settings.admin.authentication.oauthOidc.label')}
						description={$i18n.t('settings.admin.authentication.oauthOidc.description')}
						let:labelId
					>
						<Switch bind:state={oauthConfig.ENABLE_OAUTH} ariaLabelledbyId={labelId} />
					</AdminSettingRow>

					{#if oauthConfig.ENABLE_OAUTH}
						<div class="grid grid-cols-1 gap-x-3 gap-y-2.5 sm:grid-cols-2">
							<AdminSettingField
								label={$i18n.t('settings.admin.authentication.providerName.label')}
								description={$i18n.t('settings.admin.authentication.providerName.description')}
							>
								<input
									class={inputClass}
									placeholder="SSO"
									bind:value={oauthConfig.OAUTH_PROVIDER_NAME}
								/>
							</AdminSettingField>

							<AdminSettingField
								label={$i18n.t('settings.admin.authentication.providerUrl.label')}
								description={$i18n.t('settings.admin.authentication.providerUrl.description')}
							>
								<input
									class={inputClass}
									placeholder="https://accounts.google.com/.well-known/openid-configuration"
									bind:value={oauthConfig.OPENID_PROVIDER_URL}
								/>
							</AdminSettingField>
						</div>

						<div class="grid grid-cols-1 gap-x-3 gap-y-2.5 sm:grid-cols-2">
							<AdminSettingField
								label={$i18n.t('settings.admin.authentication.clientId.label')}
								description={$i18n.t('settings.admin.authentication.clientId.description')}
							>
								<input
									class={inputClass}
									placeholder={$i18n.t('Enter Client ID')}
									bind:value={oauthConfig.OAUTH_CLIENT_ID}
								/>
							</AdminSettingField>

							<AdminSettingField
								label={$i18n.t('settings.admin.authentication.clientSecret.label')}
								description={$i18n.t('settings.admin.authentication.clientSecret.description')}
							>
								<SensitiveInput
									variant="settings"
									placeholder={$i18n.t('Enter Client Secret')}
									required={false}
									bind:value={oauthConfig.OAUTH_CLIENT_SECRET}
								/>
							</AdminSettingField>
						</div>

						<div class="grid grid-cols-1 gap-x-3 gap-y-2.5 sm:grid-cols-2">
							<AdminSettingField
								label={$i18n.t('settings.admin.authentication.redirectUri.label')}
								description={$i18n.t('settings.admin.authentication.redirectUri.description')}
							>
								<input
									class={inputClass}
									placeholder={$i18n.t('Enter Redirect URI')}
									bind:value={oauthConfig.OPENID_REDIRECT_URI}
								/>
							</AdminSettingField>

							<AdminSettingField
								label={$i18n.t('settings.admin.authentication.scopes.label')}
								description={$i18n.t('settings.admin.authentication.scopes.description')}
							>
								<input
									class={inputClass}
									placeholder="openid email profile"
									bind:value={oauthConfig.OAUTH_SCOPES}
								/>
							</AdminSettingField>
						</div>

						<div class="grid grid-cols-1 gap-x-3 gap-y-2.5 sm:grid-cols-2">
							<AdminSettingField
								label={$i18n.t('settings.admin.authentication.emailClaim.label')}
								description={$i18n.t('settings.admin.authentication.emailClaim.description')}
							>
								<input
									class={inputClass}
									placeholder="email"
									bind:value={oauthConfig.OAUTH_EMAIL_CLAIM}
								/>
							</AdminSettingField>

							<AdminSettingField
								label={$i18n.t('settings.admin.authentication.usernameClaim.label')}
								description={$i18n.t('settings.admin.authentication.usernameClaim.description')}
							>
								<input
									class={inputClass}
									placeholder="name"
									bind:value={oauthConfig.OAUTH_USERNAME_CLAIM}
								/>
							</AdminSettingField>
						</div>

						<div class="grid grid-cols-1 gap-x-3 gap-y-2.5 sm:grid-cols-2">
							<AdminSettingField
								label={$i18n.t('settings.admin.authentication.pictureClaim.label')}
								description={$i18n.t('settings.admin.authentication.pictureClaim.description')}
							>
								<input
									class={inputClass}
									placeholder="picture"
									bind:value={oauthConfig.OAUTH_PICTURE_CLAIM}
								/>
							</AdminSettingField>

							<AdminSettingField
								label={$i18n.t('settings.admin.authentication.subClaim.label')}
								description={$i18n.t('settings.admin.authentication.subClaim.description')}
							>
								<input
									class={inputClass}
									placeholder="sub"
									bind:value={oauthConfig.OAUTH_SUB_CLAIM}
								/>
							</AdminSettingField>
						</div>

						<AdminSettingRow
							label={$i18n.t('settings.admin.authentication.oauthSignup.label')}
							description={$i18n.t('settings.admin.authentication.oauthSignup.description')}
							let:labelId
						>
							<Switch bind:state={oauthConfig.ENABLE_OAUTH_SIGNUP} ariaLabelledbyId={labelId} />
						</AdminSettingRow>

						<AdminSettingRow
							label={$i18n.t('settings.admin.authentication.mergeAccountsByEmail.label')}
							description={$i18n.t(
								'settings.admin.authentication.mergeAccountsByEmail.description'
							)}
							let:labelId
						>
							<Switch
								bind:state={oauthConfig.OAUTH_MERGE_ACCOUNTS_BY_EMAIL}
								ariaLabelledbyId={labelId}
							/>
						</AdminSettingRow>

						<AdminSettingRow
							label={$i18n.t('settings.admin.authentication.autoRedirect.label')}
							description={$i18n.t('settings.admin.authentication.autoRedirect.description')}
							let:labelId
						>
							<Switch bind:state={oauthConfig.OAUTH_AUTO_REDIRECT} ariaLabelledbyId={labelId} />
						</AdminSettingRow>

						<AdminSettingField
							label={$i18n.t('settings.admin.authentication.allowedDomains.label')}
							description={$i18n.t('settings.admin.authentication.allowedDomains.description')}
						>
							<input
								class={inputClass}
								placeholder={$i18n.t('* (all domains)')}
								bind:value={oauthConfig.OAUTH_ALLOWED_DOMAINS}
							/>
						</AdminSettingField>

						<!-- LICENSE covers this Open WebUI wordmark.
						Do not alter, remove, obscure, or replace it except as LICENSE permits:
						https://docs.openwebui.com/license. -->
						<AdminSettingRow
							label={$i18n.t('settings.admin.authentication.roleMapping.label')}
							description={$i18n.t('settings.admin.authentication.roleMapping.description')}
							let:labelId
						>
							<Switch
								bind:state={oauthConfig.ENABLE_OAUTH_ROLE_MANAGEMENT}
								ariaLabelledbyId={labelId}
							/>
						</AdminSettingRow>

						{#if oauthConfig.ENABLE_OAUTH_ROLE_MANAGEMENT}
							<div class="grid grid-cols-1 gap-x-3 gap-y-2.5 sm:grid-cols-2">
								<AdminSettingField
									label={$i18n.t('settings.admin.authentication.rolesClaim.label')}
									description={$i18n.t('settings.admin.authentication.rolesClaim.description')}
								>
									<input
										class={inputClass}
										placeholder="roles"
										bind:value={oauthConfig.OAUTH_ROLES_CLAIM}
									/>
								</AdminSettingField>

								<AdminSettingField
									label={$i18n.t('settings.admin.authentication.adminRoles.label')}
									description={$i18n.t('settings.admin.authentication.adminRoles.description')}
								>
									<input
										class={inputClass}
										placeholder="admin"
										bind:value={oauthConfig.OAUTH_ADMIN_ROLES}
									/>
								</AdminSettingField>
							</div>

							<AdminSettingField
								label={$i18n.t('settings.admin.authentication.allowedRoles.label')}
								description={$i18n.t('settings.admin.authentication.allowedRoles.description')}
							>
								<input
									class={inputClass}
									placeholder="*"
									bind:value={oauthConfig.OAUTH_ALLOWED_ROLES}
								/>
							</AdminSettingField>
						{/if}

						<!-- LICENSE covers this Open WebUI wordmark.
						Do not alter, remove, obscure, or replace it except as LICENSE permits:
						https://docs.openwebui.com/license. -->
						<AdminSettingRow
							label={$i18n.t('settings.admin.authentication.enableOauthGroupManagement.label')}
							description={$i18n.t(
								'settings.admin.authentication.enableOauthGroupManagement.description'
							)}
							let:labelId
						>
							<Switch
								bind:state={oauthConfig.ENABLE_OAUTH_GROUP_MANAGEMENT}
								ariaLabelledbyId={labelId}
							/>
						</AdminSettingRow>

						{#if oauthConfig.ENABLE_OAUTH_GROUP_MANAGEMENT}
							<AdminSettingRow
								label={$i18n.t('settings.admin.authentication.enableOauthGroupCreation.label')}
								description={$i18n.t(
									'settings.admin.authentication.enableOauthGroupCreation.description'
								)}
								let:labelId
							>
								<Switch
									bind:state={oauthConfig.ENABLE_OAUTH_GROUP_CREATION}
									ariaLabelledbyId={labelId}
								/>
							</AdminSettingRow>

							<div class="grid grid-cols-1 gap-x-3 gap-y-2.5 sm:grid-cols-2">
								<AdminSettingField
									label={$i18n.t('settings.admin.authentication.groupClaim.label')}
									description={$i18n.t('settings.admin.authentication.groupClaim.description')}
								>
									<input
										class={inputClass}
										placeholder="groups"
										bind:value={oauthConfig.OAUTH_GROUP_CLAIM}
									/>
								</AdminSettingField>

								<AdminSettingField
									label={$i18n.t('settings.admin.authentication.blockedGroups.label')}
									description={$i18n.t('settings.admin.authentication.blockedGroups.description')}
								>
									<input
										class={inputClass}
										placeholder={$i18n.t('Comma-separated group names')}
										bind:value={oauthConfig.OAUTH_BLOCKED_GROUPS}
									/>
								</AdminSettingField>
							</div>
						{/if}

						<AdminSettingRow
							label={$i18n.t('settings.admin.authentication.updateEmail.label')}
							description={$i18n.t('settings.admin.authentication.updateEmail.description')}
							let:labelId
						>
							<Switch
								bind:state={oauthConfig.OAUTH_UPDATE_EMAIL_ON_LOGIN}
								ariaLabelledbyId={labelId}
							/>
						</AdminSettingRow>

						<AdminSettingRow
							label={$i18n.t('settings.admin.authentication.updateName.label')}
							description={$i18n.t('settings.admin.authentication.updateName.description')}
							let:labelId
						>
							<Switch
								bind:state={oauthConfig.OAUTH_UPDATE_NAME_ON_LOGIN}
								ariaLabelledbyId={labelId}
							/>
						</AdminSettingRow>

						<AdminSettingRow
							label={$i18n.t('settings.admin.authentication.updatePicture.label')}
							description={$i18n.t('settings.admin.authentication.updatePicture.description')}
							let:labelId
						>
							<Switch
								bind:state={oauthConfig.OAUTH_UPDATE_PICTURE_ON_LOGIN}
								ariaLabelledbyId={labelId}
							/>
						</AdminSettingRow>
					{/if}
				</fieldset>
			</AdminSettingSection>
		{/if}
	</div>

	<div class="flex justify-end pt-6 text-sm font-normal">
		<button
			class="px-3.5 py-1.5 text-sm font-normal bg-black hover:bg-gray-900 text-white dark:bg-white dark:text-black dark:hover:bg-gray-100 transition rounded-full"
			type="submit"
		>
			{$i18n.t('Save')}
		</button>
	</div>
</form>

<Modal bind:show={showPickerUserModal} size="sm">
	<div
		class="px-5 py-4 text-gray-700 dark:text-gray-200"
		on:keydown={(event) => {
			if (event.key === 'Enter' && !(event.target instanceof HTMLButtonElement)) {
				event.preventDefault();
				savePickerUserDraft();
			}
		}}
	>
		<div class="mb-3 flex items-center justify-between">
			<div class="text-sm font-medium">
				{$i18n.t('settings.admin.authentication.userPickerAdd.label')}
			</div>
			<button
				class="rounded-lg p-1 text-gray-500 transition hover:bg-gray-50 hover:text-gray-700 dark:text-gray-400 dark:hover:bg-gray-800 dark:hover:text-gray-200"
				type="button"
				aria-label={$i18n.t('Close')}
				on:click={() => {
					showPickerUserModal = false;
				}}
			>
				<XMark className="size-4" />
			</button>
		</div>
		<p class="mb-3 text-xs text-gray-500 dark:text-gray-400">
			{$i18n.t(
				'This person will appear on the login page. They still need their password to sign in.'
			)}
		</p>
		<div class="flex flex-col gap-2">
			<label class="text-xs text-gray-500" for="picker-user-name">
				{$i18n.t('settings.admin.authentication.userPickerDisplayName.label')}
			</label>
			<input
				id="picker-user-name"
				class="w-full rounded-lg border border-gray-100/50 bg-transparent px-2 py-1.5 text-sm outline-hidden dark:border-white/10"
				type="text"
				autocomplete="off"
				bind:value={pickerUserDraft.name}
			/>
			<label class="text-xs text-gray-500" for="picker-user-email">
				{$i18n.t('settings.admin.authentication.userPickerEmail.label')}
			</label>
			<input
				id="picker-user-email"
				class="w-full rounded-lg border border-gray-100/50 bg-transparent px-2 py-1.5 text-sm outline-hidden dark:border-white/10"
				type="text"
				autocomplete="off"
				bind:value={pickerUserDraft.email}
			/>
			<label class="text-xs text-gray-500" for="picker-user-avatar">
				{$i18n.t('settings.admin.authentication.userPickerAvatar.label')}
			</label>
			<input
				id="picker-user-avatar"
				class="w-full rounded-lg border border-gray-100/50 bg-transparent px-2 py-1.5 text-sm outline-hidden dark:border-white/10"
				type="text"
				autocomplete="off"
				placeholder="https://"
				bind:value={pickerUserDraft.profile_image_url}
			/>
		</div>
		<div class="mt-4 flex justify-end gap-2">
			<button
				class="rounded-full px-3.5 py-1.5 text-sm text-gray-600 hover:bg-gray-100 dark:text-gray-300 dark:hover:bg-gray-800"
				type="button"
				on:click={() => {
					showPickerUserModal = false;
				}}
			>
				{$i18n.t('Cancel')}
			</button>
			<button
				class="rounded-full bg-black px-3.5 py-1.5 text-sm text-white hover:bg-gray-900 dark:bg-white dark:text-black dark:hover:bg-gray-100"
				type="button"
				on:click={savePickerUserDraft}
			>
				{$i18n.t('Save')}
			</button>
		</div>
	</div>
</Modal>
