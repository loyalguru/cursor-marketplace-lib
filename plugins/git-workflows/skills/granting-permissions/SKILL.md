---
name: granting-permissions
description: >-
  Use when a Customer Success or data-team ticket approved granting a Management
  API permission in Staging or Production, or when the user asks to run
  permissions:create_permission / permissions:add_role_permission via the
  rails-console bastion.
---

# Granting permissions

## Overview

After approval, create the permission on **live** Staging or Production and attach it to the agreed roles. Code-side work (Pundit, `Role.permissions_table`) is separate — do not mix that checklist into this runbook.

Propose each command. Run only after an explicit ok. The engineer pastes into the bastion interactive Ruby console — this environment has no terminal into the bastion.

## When to use

- Approval ticket says the rake may run
- Staging (`senor-1099`) or Production (`streaming-west`), zone `europe-west1-b`, virtual private network already up

**Not for:** writing the Grape endpoint, locales, or policies. Do not install Go or `rconsole` on the laptop.

## Open the console

List revisions, then open one. Service `management-api`, or Staging preview `auto-management-<actor>-<PR>` (same Staging database).

```bash
gcloud --project="senor-1099" compute ssh rails-console-bastion \
  --zone="europe-west1-b" --tunnel-through-iap \
  --command="console management-api --list" -- -t
```

```bash
gcloud --project="senor-1099" compute ssh rails-console-bastion \
  --zone="europe-west1-b" --tunnel-through-iap \
  --command="console management-api --revision REVISION" -- -t
```

Production: same with `--project="streaming-west"`. If the instance is stopped: start `rails-console-bastion` in that project first.

## Map roles before any write

```ruby
Apartment::Tenant.switch('public') do
  GlobalRole.order(:name).pluck(:name, :internal, :legacy)
end
```

| Ticket label | GlobalRole slug | Legacy Role name |
| --- | --- | --- |
| Owner | `owner` | `owner` |
| Support Lead | `support_lead` | — |
| Internal LG | `internal_lg` | `internal` |
| Super Admin | `super_admin_lg` | — |
| Admin | — | `admin` |
| Manager | `manager` | `manager` |
| Customer Service | `customer_service` | `customer_service` |

Confirm slugs via `pluck`. Never invent roles. Missing legacy role on one company (`role not found`) is expected.

## New system (`public`)

```ruby
puts system(%q{bundle exec rake 'permissions:create_permission[Customer@export,customers,false,true,owner,support_lead]'})
```

Args: identifier `Resource@action`, group slug, `basic`, `visible`, then **slugs**.

```ruby
Apartment::Tenant.switch('public') do
  p = Permission.find_by!(identifier: 'Customer@export')
  puts "id=#{p.id} basic=#{p.basic} visible=#{p.visible}"
  puts p.roles.order(:name).pluck(:name).inspect
end
```

Do not `joins(:permissions)` on `GlobalRole` — use `Permission#roles`.

## Legacy (until 31/12/2026)

One rake per legacy role name (walks every company):

```ruby
puts system(%q{bundle exec rake "permissions:add_role_permission[owner,Customer@export]"})
```

Spot-check on a real company:

```ruby
Apartment::Tenant.switch('mango') do
  %w[owner admin].each do |name|
    r = Role.find_by(name: name)
    puts "#{name}: #{r&.permissions&.include?('Customer@export') ? 'OK' : 'MISSING'}"
  end
end
```

Do not `update!(permissions: ...)` by hand. Do not assign roles the ticket did not list (including provisional `user_manager` from `permissions_table` only).

## Common mistakes

| Mistake | Fix |
| --- | --- |
| Role name = ticket label (`"Support Lead"`) | Use slug from `pluck` |
| `Permission.name` / `group:` | Columns are `identifier`, `permission_group`; the rake sets them |
| Treat Cloud Run preview as another database | Shares Staging `public` and company schemas |
| Pub/Sub `PermissionDenied` in bastion logs | Noise if rake already printed Created / Assigned / Done |
