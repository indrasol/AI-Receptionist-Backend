-- Migration: Auto-create profiles and organizations when user signs up via OTP
-- This trigger fires when Supabase Auth creates a new user after OTP verification
-- The user's metadata (stored during OTP request) is used to create profile and organization

-- ⚠️ IMPORTANT: Run this through Supabase Dashboard SQL Editor
-- Dashboard → SQL Editor → New Query → Paste & Run

-- ============================================================
-- STEP 1: Remove old trigger and function (if they exist)
-- ============================================================

-- Drop the old trigger
DROP TRIGGER IF EXISTS on_auth_user_created ON auth.users;

-- Drop the old function (this will also drop any triggers using it)
DROP FUNCTION IF EXISTS public.handle_new_user() CASCADE;

-- Verify they're gone (optional check)
-- SELECT tgname, tgenabled FROM pg_trigger WHERE tgname = 'on_auth_user_created';

-- ============================================================
-- STEP 2: Create new enhanced trigger and function
-- ============================================================

-- Function to handle new user signup with organization creation
CREATE OR REPLACE FUNCTION public.handle_new_user_signup()
RETURNS TRIGGER
LANGUAGE plpgsql
SECURITY DEFINER              -- Run with elevated privileges
SET search_path = public      -- Access public schema tables
AS $$
DECLARE
  v_org_id UUID;
  v_org_name TEXT;
  v_first_name TEXT;
  v_last_name TEXT;
  v_is_signup BOOLEAN;
BEGIN
  -- ⚠️ CRITICAL: Only process if email is confirmed (OTP verified)
  -- This prevents creating profiles for unverified users
  -- Field is called 'confirmed_at' not 'email_confirmed_at'
  IF new.confirmed_at IS NULL THEN
    RAISE LOG 'Skipping profile creation - email not confirmed yet for: %', new.email;
    RETURN new;
  END IF;
  
  -- Extract metadata from raw_user_meta_data
  v_org_name := new.raw_user_meta_data->>'organization_name';
  v_first_name := new.raw_user_meta_data->>'first_name';
  v_last_name := new.raw_user_meta_data->>'last_name';
  
  -- Safely convert signup_flow to boolean (handle null/invalid values)
  BEGIN
    v_is_signup := (new.raw_user_meta_data->>'signup_flow')::boolean;
  EXCEPTION WHEN OTHERS THEN
    v_is_signup := false;
  END;
  
  -- Only process if this is a signup flow (has signup_flow flag = true)
  IF COALESCE(v_is_signup, false) = true THEN
    
    RAISE LOG 'Processing new user signup for email: %', new.email;
    
    -- Step 1: Create or find organization (if organization name is provided)
    IF v_org_name IS NOT NULL AND BTRIM(v_org_name) <> '' THEN
      
      -- Check if organization already exists (case-insensitive)
      SELECT id INTO v_org_id
      FROM organizations
      WHERE LOWER(name) = LOWER(v_org_name)
      LIMIT 1;
      
      -- Create new organization if it doesn't exist
      IF v_org_id IS NULL THEN
        INSERT INTO organizations (name, created_at, updated_at)
        VALUES (v_org_name, NOW(), NOW())
        RETURNING id INTO v_org_id;
        
        RAISE LOG 'Created new organization: % with ID: %', v_org_name, v_org_id;
      ELSE
        RAISE LOG 'Using existing organization: % with ID: %', v_org_name, v_org_id;
      END IF;
      
    END IF;
    
    -- Step 2: Create user profile (if it doesn't already exist)
    IF NOT EXISTS (SELECT 1 FROM profiles WHERE email = new.email) THEN
      INSERT INTO profiles (
        user_id,
        email,
        organization_id,
        first_name,
        last_name,
        created_at,
        updated_at
      )
      VALUES (
        new.id,
        new.email,
        v_org_id,
        v_first_name,
        v_last_name,
        new.created_at,
        NOW()
      );
      
      RAISE LOG 'Created profile for user: % with org_id: %', new.email, v_org_id;
    ELSE
      RAISE LOG 'Profile already exists for user: %', new.email;
    END IF;
    
  ELSE
    -- This is a login flow or user created without metadata - skip profile creation
    RAISE LOG 'Skipping profile creation - not a signup flow: %', new.email;
  END IF;
  
  RETURN new;

EXCEPTION
  WHEN OTHERS THEN
    -- Log the error but don't fail the user creation
    RAISE WARNING 'Error in handle_new_user_signup for %: %', new.email, SQLERRM;
    RETURN new;
END;
$$;

-- Drop existing trigger if it exists
DROP TRIGGER IF EXISTS on_auth_user_created ON auth.users;

-- Create trigger on auth.users table
-- Fires AFTER INSERT (user created) OR UPDATE (email confirmed)
-- The function checks if email is confirmed before creating profile
CREATE TRIGGER on_auth_user_created
  AFTER INSERT OR UPDATE ON auth.users
  FOR EACH ROW
  EXECUTE FUNCTION public.handle_new_user_signup();
