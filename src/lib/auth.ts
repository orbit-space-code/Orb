import { NextAuthOptions, Session, User } from "next-auth"
import { JWT } from "next-auth/jwt"
import { AdapterUser } from "next-auth/adapters"
import GithubProvider from "next-auth/providers/github"
import { PrismaAdapter } from "@next-auth/prisma-adapter"
import { prisma } from "./prisma"
import { Account, Profile } from "next-auth"

// Extend the built-in session types
declare module "next-auth" {
  interface Session {
    user: {
      id: string
      name?: string | null
      email?: string | null
      image?: string | null
    }
  }
}

export const authOptions: NextAuthOptions = {
  adapter: PrismaAdapter(prisma),
  providers: [
    GithubProvider({
      clientId: process.env.GITHUB_CLIENT_ID!,
      clientSecret: process.env.GITHUB_CLIENT_SECRET!,
      authorization: {
        params: {
          scope: "read:user user:email repo",
        },
      },
    }),
  ],
  callbacks: {
    async session({ session, user }: { session: Session; token: JWT; user: AdapterUser }) {
      if (session.user) {
        session.user.id = user.id
      }
      return session
    },
    async signIn({ user, account, profile }: { user: User | AdapterUser; account: Account | null; profile?: Profile }) {
      if (account?.provider === "github" && profile) {
        // Store GitHub access token for repository operations
        const githubProfile = profile as any
        await prisma.user.upsert({
          where: { githubId: githubProfile.id },
          update: {
            accessToken: account.access_token!,
            username: githubProfile.login,
            email: githubProfile.email,
            avatarUrl: githubProfile.avatar_url,
          },
          create: {
            githubId: githubProfile.id,
            username: githubProfile.login,
            email: githubProfile.email,
            avatarUrl: githubProfile.avatar_url,
            accessToken: account.access_token!,
          },
        })
      }
      return true
    },
  },
  pages: {
    signIn: "/",
  },
  session: {
    strategy: "database",
  },
}
