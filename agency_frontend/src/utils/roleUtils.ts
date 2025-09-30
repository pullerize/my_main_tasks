/**
 * Utility functions for role-based access control
 */

/**
 * Check if user has admin privileges
 * @param role - User role from localStorage or props
 * @returns boolean indicating if user is admin
 */
export const isAdmin = (role: string | null): boolean => {
  if (!role) return false;

  // Normalize role and check all possible admin variants
  const normalizedRole = role.toLowerCase().trim();
  return normalizedRole === 'admin' ||
         normalizedRole === 'administrator' ||
         role === 'ADMIN';
};

/**
 * Check if user has any of the specified roles
 * @param userRole - User role from localStorage or props
 * @param allowedRoles - Array of allowed roles
 * @returns boolean indicating if user has one of the allowed roles
 */
export const hasRole = (userRole: string | null, allowedRoles: string[]): boolean => {
  if (!userRole) return false;
  return allowedRoles.includes(userRole);
};

/**
 * Check if user can access admin features
 * @param role - User role from localStorage or props
 * @returns boolean indicating if user can access admin features
 */
export const canAccessAdminFeatures = (role: string | null): boolean => {
  return isAdmin(role);
};

/**
 * Get current user role from localStorage
 * @returns string | null - User role or null if not found
 */
export const getCurrentUserRole = (): string | null => {
  return localStorage.getItem('role');
};

/**
 * Check if current user is admin
 * @returns boolean indicating if current user is admin
 */
export const isCurrentUserAdmin = (): boolean => {
  return isAdmin(getCurrentUserRole());
};