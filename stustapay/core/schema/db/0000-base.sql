-- revision: 62df6b55
-- requires: null

-- stustapay core database
--
-- (c) 2022-2023 Jonas Jelten <jj@sft.lol>
-- (c) 2022-2023 Leo Fahrbach <leo.fahrbach@stusta.de>
--
-- targets >=postgresql-13
--
-- double-entry bookkeeping for festival payment system.
-- - user identification through tokens
-- - accounts for users, ware input/output and payment providers
-- - products with custom tax rates
-- - till configuration profiles

-- security definer functions are executed in setuid-mode
-- to grant access to them, use:
--   grant execute on function some_function_name to some_insecure_user;

begin;

set plpgsql.extra_warnings to 'all';


-------- tables

-- general key-value config
create table if not exists config (
    key text not null primary key,
    value text
);
insert into config (
    key, value
)
values
    -- event organizer name
    ('bon.issuer', 'der verein'),
    -- event organizer address
    ('bon.addr', E'Müsterstraße 12\n12398 Test Stadt'),
    -- title on top of the bon. This usually is the name of the event like StuStaCulum 2023
    ('bon.title', 'StuStaCulum 2023'),
    -- json array. One of the strings is printed at the end of a bon
    ('bon.closing_texts', '["funny text 0", "funny text 1", "funny text 2", "funny text 3"]'),

    -- Umsatzsteuer ID. Needed on each bon
    ('ust_id', 'DE123456789'),
    ('currency.symbol', '€'),
    ('currency.identifier', 'EUR')
    on conflict do nothing;


create table if not exists restriction_type (
    name text not null primary key
);
insert into restriction_type (
    name
)
values
    ('under_18'),
    ('under_16')
    on conflict do nothing;


-- some secret about one or many user_tags
create table if not exists user_tag_secret (
    id bigserial not null primary key
);

-- for wristbands/cards/...
create table if not exists user_tag (
    -- hardware id of the tag
    uid numeric(20) primary key,
    -- printed on the back
    pin text,
    -- produced by wristband vendor
    serial text,
    -- age restriction information
    restriction text references restriction_type(name),

    -- to validate tag authenticity
    -- secret maybe shared with several tags.
    secret bigint references user_tag_secret(id) on delete restrict
);


create table if not exists account_type (
    name text not null primary key
);
insert into account_type (
    name
)
values
    -- for entry/exit accounts
    ('virtual'),

    -- for safe, backpack, ec, ...
    ('internal'),

    -- the one you buy drinks with
    ('private')

    -- todo: cash_drawer, deposit,
    on conflict do nothing;



-- bookkeeping account
create table if not exists account (
    id bigserial not null primary key,
    user_tag_uid numeric(20) unique references user_tag(uid) on delete cascade,
    type text not null references account_type(name) on delete restrict,
    constraint private_account_requires_user_tag check (user_tag_uid is not null = (type = 'private')),
    name text,
    comment text,

    -- current balance, updated on each transaction
    balance numeric not null default 0,
    -- current number of vouchers, updated on each transaction
    vouchers bigint not null default 0


    -- todo: voucher
    -- todo: topup-config
);
insert into account (
    id, user_tag_uid, type, name, comment
)
values
    -- virtual accounts are hard coded with ids 0-99
    (0, null, 'virtual', 'Sale Exit', 'target account for sales of the system'),
    (1, null, 'virtual', 'Cash Entry', 'source account, when cash is brought in the system (cash top_up, ...)'),
    (2, null, 'virtual', 'Deposit', 'Deposit currently at the customers'),
    (3, null, 'virtual', 'Sumup', 'source account for sumup top up '),
    (4, null, 'virtual', 'Cash Vault', 'Main Cash tresor. At some point cash top up lands here'),
    (5, null, 'virtual', 'Imbalace', 'Imbalance on a cash register on settlement'),
    (6, null, 'virtual', 'Cashing Up', 'Upon cashing up a cashier for a till a 0 transaction will be booked to this account to mark the cashing up time')
    on conflict do nothing;
select setval('account_id_seq', 100);


-- people working with the payment system
create table if not exists usr (
    id serial not null primary key,

    name text not null unique,
    password text,
    description text,

    user_tag_uid numeric(20) unique references user_tag(uid) on delete restrict,

    -- account for orgas to transport cash from one location to another
    transport_account_id bigint references account(id) on delete restrict,
    -- account for cashiers to store the current cash balance in input or output locations
    cashier_account_id bigint references account(id) on delete restrict
    -- depending on the transfer action, the correct account is booked

    constraint password_or_user_tag_id_set check ((user_tag_uid is not null) or (password is not null))
);


create table if not exists usr_session (
    id serial not null primary key,
    usr int not null references usr(id) on delete cascade
);


create table if not exists privilege (
    name text not null primary key
);
insert into privilege (
    name
)
values
    -- Super Use
    ('admin'),
    -- Finanzorga
    ('finanzorga'),
    -- Standleiter
    -- ('orga'),
    -- Helfer
    ('cashier')
    on conflict do nothing;

create table if not exists usr_privs (
    usr int not null references usr(id) on delete cascade,
    priv text not null references privilege(name) on delete cascade,
    primary key (usr, priv)
);

create or replace view usr_with_privileges as (
    select
        usr.*,
        coalesce(privs.privs, '{}'::text array) as privileges
    from usr
    left join (
        select p.usr as user_id, array_agg(p.priv) as privs
        from usr_privs p
        group by p.usr
    ) privs on usr.id = privs.user_id
);

create table if not exists payment_method (
    name text not null primary key
);
insert into payment_method (
    name
)
values
    -- when topping up with cash
    ('cash'),

    -- when topping up with ec
    ('ec'),

    -- payment with token
    ('token')

    -- todo: paypal

    on conflict do nothing;

create table if not exists order_type(
    name text not null primary key
);
insert into order_type (
    name
)
values
    -- load token with cash
    ('topup_cash'),
    -- load token with sumup
    ('topup_sumup'),
    -- buy items to consume
    ('sale')
    on conflict do nothing;


create table if not exists tax (
    name text not null primary key,
    rate numeric not null,
    description text not null
);
insert into tax (
    name, rate, description
)
values
    -- for internal transfers, THIS LINE MUST NOT BE DELETED, EVEN BY AN ADMIN
    ('none', 0.0, 'keine Steuer'),

    -- reduced sales tax for food etc
    -- ermäßigte umsatzsteuer in deutschland
    ('eust', 0.07, 'ermäßigte Umsatzsteuer'),

    -- normal sales tax
    -- umsatzsteuer in deutschland
    ('ust', 0.19, 'normale Umsatzsteuer')

    on conflict do nothing;


create table if not exists product (
    id serial not null primary key,
    -- todo: ean or something for receipt?
    name text not null unique,
    -- price including tax (what is charged in the end)
    price numeric,
    -- price is not fixed, e.g for top up. Then price=null and set with the api call
    fixed_price boolean not null default true,
    price_in_vouchers bigint, -- will be null if this product cannot be bought with vouchers
    constraint product_vouchers_only_with_fixed_price check ( price_in_vouchers is not null and fixed_price or price_in_vouchers is null ),
    constraint product_not_fixed_or_price check ( price is not null = fixed_price),

    -- whether the core metadata of this product (price, price_in_vouchers, fixed_price, tax_name and target_account_id) is editable
    is_locked bool not null default false,

    -- if target account is set, the product is booked to this specific account,
    -- e.g. for the deposit account, or a specific exit account (for beer, ...)
    target_account_id int references account(id) on delete restrict,

    tax_name text not null references tax(name) on delete restrict
);

insert into product (id, name, fixed_price, tax_name, is_locked)
values (1, 'Rabatt', false, 'none', true);
select setval('product_id_seq', 100);

-- which products are not allowed to be bought with the user tag restriction (eg beer, below 16)
create table if not exists product_restriction (
    id          bigint not null references product (id) on delete cascade,
    restriction text   not null references restriction_type (name) on delete restrict,
    primary key (id, restriction)
);

create or replace view product_with_tax_and_restrictions as (
    select
        p.*,
        tax.rate as tax_rate,
        coalesce(pr.restrictions, '{}'::text array) as restrictions
    from product p
    join tax on p.tax_name = tax.name
    left join (
        select r.id, array_agg(r.restriction) as restrictions
        from product_restriction r
        group by r.id
    ) pr on pr.id = p.id
);

create or replace view product_as_json as (
    select p.id, json_agg(p)->0 as json
    from product_with_tax_and_restrictions p
    group by p.id
);

create table if not exists till_layout (
    id serial not null primary key,
    name text not null unique,
    description text
);

create table if not exists till_button (
    id serial not null primary key,
    name text not null unique
);

create table if not exists till_button_product (
    button_id int not null references till_button(id) on delete cascade,
    product_id int not null references product(id) on delete cascade,
    primary key (button_id, product_id)
    -- TODO: constraint that we can only reference non-editable products
);

create or replace view till_button_with_products as (
    select
        t.*,
        coalesce(j_view.price, 0) as price,
        coalesce(j_view.product_ids, '{}'::int array) as product_ids
    from till_button t
    left join (
        select tlb.button_id, sum(p.price) as price, array_agg(tlb.product_id) as product_ids
        from till_button_product tlb
        join product_with_tax_and_restrictions p on tlb.product_id = p.id
        group by tlb.button_id
    ) j_view on t.id = j_view.button_id
);

create table if not exists till_layout_to_button (
    layout_id int not null references till_layout(id) on delete cascade,
    button_id int not null references till_button(id) on delete restrict,
    sequence_number int not null unique,
    primary key (layout_id, button_id)
);

create or replace view till_layout_with_buttons as (
    select t.*, coalesce(j_view.button_ids, '{}'::int array) as button_ids
    from till_layout t
    left join (
        select tltb.layout_id, array_agg(tltb.button_id order by tltb.sequence_number) as button_ids
        from till_layout_to_button tltb
        group by tltb.layout_id
    ) j_view on t.id = j_view.layout_id
);

create table if not exists till_profile (
    id serial not null primary key,
    name text not null unique,
    description text,
    allow_top_up boolean not null default false,
    layout_id int not null references till_layout(id) on delete restrict
    -- todo: payment_methods?
);

-- which cash desks do we have and in which state are they
create table if not exists till (
    id serial not null primary key,
    name text not null unique,
    description text,
    registration_uuid uuid unique,
    session_uuid uuid unique,

    -- how this till is mapped to a tse
    tse_id text,

    -- identifies the current active work shift and configuration
    active_shift text,
    active_profile_id int not null references till_profile(id) on delete restrict,
    active_user_id int references usr(id) on delete restrict,

    constraint registration_or_session_uuid_null check ((registration_uuid is null) != (session_uuid is null))
);

-- represents an order of an customer, like buying wares or top up
create table if not exists ordr (
    id bigserial not null primary key,
    uuid uuid not null default gen_random_uuid() unique,

    -- order values can be obtained with order_value

    -- how many line items does this transaction have
    -- determines the next line_item id
    item_count int not null default 0,

    booked_at timestamptz not null default now(),

    -- todo: who triggered the transaction (user)

    -- how the order was invoked
    payment_method text references payment_method(name) on delete restrict,
    -- todo: method_info references payment_information(id) -> (sumup-id, paypal-id, ...)
    --       or inline-json without separate table?

    -- type of the order like, top up, buy beer,
    order_type text not null references order_type(name) on delete restrict,

    -- who created it
    cashier_id int not null references usr(id) on delete restrict,
    till_id int not null references till(id) on delete restrict,
    -- customer is allowed to be null, as it is only known on the final booking, not on the creation of the order
    -- canceled orders can have no customer
    customer_account_id int references account(id) on delete restrict
);

-- all products in a transaction
create table if not exists line_item (
    order_id bigint not null references ordr(id) on delete cascade,
    item_id int not null,
    primary key(order_id, item_id),

    product_id int not null references product(id) on delete restrict,

    quantity int not null default 1,
    constraint quantity_positive check ( quantity > 0 ),

    -- price with tax
    price numeric not null,

    -- tax amount
    tax_name text,
    tax_rate numeric
);

create or replace function order_updated() returns trigger as
$$
begin
    -- A deletion should only be able to occur for uncommitted revisions
    if NEW is null then
        return null;
    end if;
    perform pg_notify(
        'order',
        json_build_object(
            'order_id', NEW.id,
            'order_uuid', NEW.uuid,
            'cashier_id', NEW.cashier_id,
            'till_id', NEW.till_id
        )::text
    );

    return null;
end;
$$ language plpgsql;

drop trigger if exists order_updated_trigger on ordr;
create trigger order_updated_trigger
    after insert or update
    on ordr
    for each row
execute function order_updated();

create or replace view line_item_tax as
    select
        l.*,
        l.price * l.quantity as total_price,
        round(l.price * l.quantity * l.tax_rate / (1 + l.tax_rate ), 2) as total_tax,
        p.json as product
    from line_item l join product_as_json p on l.product_id = p.id;

-- aggregates the line_item's amounts
create or replace view order_value as
    select
        ordr.*,
        sum(total_price) as total_price,
        sum(total_tax) as total_tax,
        sum(total_price - total_tax) as total_no_tax,
        json_agg(line_item_tax) as line_items
    from
        ordr
        left join line_item_tax
            on (ordr.id = line_item_tax.order_id)
    group by
        ordr.id;

-- show all line items
create or replace view order_items as
    select
        ordr.*,
        line_item.*
    from
        ordr
        left join line_item
            on (ordr.id = line_item.order_id);

-- aggregated tax rate of items
create or replace view order_tax_rates as
    select
        ordr.*,
        tax_name,
        tax_rate,
        sum(total_price) as value_sum,
        sum(total_tax) as value_tax,
        sum(total_price - total_tax) as value_notax
    from
        ordr
        left join line_item_tax
            on (ordr.id = order_id)
        group by
            ordr.id, tax_rate, tax_name;


create table if not exists transaction (
    -- represents a transaction of one account to another
    -- one order can consist of multiple transactions, hence the extra table
    --      e.g. wares to the ware output account
    --      and deposit to a specific deposit account
    id bigserial not null primary key,
    order_id bigint references ordr(id) on delete restrict,

    -- what was booked in this transaction  (backpack, items, ...)
    description text,

    source_account int not null references account(id) on delete restrict,
    target_account int not null references account(id) on delete restrict,
    constraint source_target_account_different check (source_account != target_account),

    booked_at timestamptz not null default now(),

    -- amount being transferred from source_account to target_account
    amount numeric not null,
    constraint amount_positive check (amount >= 0),
    vouchers bigint not null,
    constraint vouchers_positive check (vouchers >= 0)
);


create or replace view cashiers as (
    select
        usr.id,
        usr.name,
        usr.description,
        usr.user_tag_uid,
        a.balance as cash_drawer_balance,
        t.id as till_id
    from usr
    join account a on usr.cashier_account_id = a.id
    left join till t on t.active_user_id = usr.id
);


-- book a new transaction and update the account balances automatically, returns the new transaction_id
create or replace function book_transaction (
    order_id bigint,
    description text,
    source_account_id bigint,
    target_account_id bigint,
    amount numeric,
    vouchers_amount bigint
)
    returns bigint as $$
<<locals>> declare
    transaction_id bigint;
    temp_account_id bigint;
begin
    if vouchers_amount < 0 then
        raise 'vouchers cannot be negative';
    end if;

    if amount < 0 then
        -- swap account on negative amount, as only non-negative transactions are allowed
        temp_account_id = source_account_id;
        source_account_id = target_account_id;
        target_account_id = temp_account_id;
        amount = -amount;
    end if;

    -- add new transaction
    insert into transaction (
        order_id, description, source_account, target_account, amount, vouchers
    )
    values (
        book_transaction.order_id,
        book_transaction.description,
        book_transaction.source_account_id,
        book_transaction.target_account_id,
        book_transaction.amount,
        book_transaction.vouchers_amount
    ) returning id into locals.transaction_id;

    -- update account values
    update account set
        balance = balance - amount,
        vouchers = vouchers - vouchers_amount
        where id = source_account_id;
    update account set
        balance = balance + amount,
        vouchers = vouchers + vouchers_amount
        where id = target_account_id;

    return locals.transaction_id;

end;
$$ language plpgsql;


-- requests the tse module to sign something
create table if not exists tse_signature (
    id serial not null primary key references ordr(id) on delete cascade,

    signed bool default false,
    status text,

    tse_transaction text,
    tse_signaturenr text,
    tse_start       text,
    tse_end         text,
    tse_serial      text,
    tse_hashalgo    text,
    tse_signature   text
);


-- requests the bon generator to create a new receipt
create table if not exists bon (
    id bigint not null primary key references ordr(id) on delete cascade,

    generated bool default false,
    generated_at timestamptz,
    status text,
    -- latex compile error
    error text,

    -- output file path
    output_file text
);


-- wooh \o/
commit;
